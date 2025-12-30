"""
Tokens Router - Token accounting, usage tracking, cost analysis, and alerts.
"""

import json
import logging
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional, List, Dict, Any, Literal

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from utils import get_db, dict_from_row

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tokens", tags=["tokens"])

# Cache TTL in seconds (5 minutes)
_CACHE_TTL = 300
_cache_timestamp: float = 0
_cache_lock = threading.Lock()  # Thread-safe cache access

CLAUDE_PROJECTS_PATH = Path.home() / ".claude" / "projects"

# Number of lines to read from end of JSONL files when scanning for token usage.
# Must be large enough to find lastModelUsage entry past trailing empty lines,
# non-usage log entries, and potential file corruption. 200 provides good margin
# while staying memory-efficient (8KB typical for 200 JSON lines).
JSONL_TAIL_LINES = 200

# Whitelist of allowed fields for alert updates (SQL injection protection).
# Defense-in-depth: Pydantic validates field types/values at the model layer,
# this whitelist validates field names before SQL construction.
ALERT_UPDATE_ALLOWED_FIELDS = {"alert_type", "threshold_value", "threshold_unit", "time_window", "is_enabled"}


class TokenAlertCreate(BaseModel):
    alert_type: str
    threshold_value: float
    threshold_unit: Literal["tokens", "usd", "percent"]
    time_window: str = "daily"
    is_enabled: bool = True


class TokenAlertUpdate(BaseModel):
    alert_type: Optional[str] = None
    threshold_value: Optional[float] = None
    threshold_unit: Optional[Literal["tokens", "usd", "percent"]] = None
    time_window: Optional[str] = None
    is_enabled: Optional[bool] = None


@lru_cache(maxsize=None)
def ensure_tables_exist():
    """Ensure token tables exist - only runs once per application lifecycle.

    Uses @lru_cache for thread-safe one-time initialization. While lru_cache
    isn't atomic, CREATE TABLE IF NOT EXISTS is idempotent, so concurrent
    calls during initial startup are harmless.

    Note: token_metrics table is provisioned for future persistent storage.
    Currently, token data is computed from JSONL files and cached in memory.
    The table is NOT populated in this sprint - this is intentional.

    Future enhancement (separate sprint):
    - Add source='historical' when populating from JSONL files
    - Add source='realtime' for webhook-based live capture
    - Migrate endpoints to query DB instead of in-memory cache
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS token_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                project_path TEXT,
                model TEXT NOT NULL,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                cache_read_tokens INTEGER DEFAULT 0,
                cache_creation_tokens INTEGER DEFAULT 0,
                web_search_requests INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0.0,
                source TEXT NOT NULL CHECK(source IN ('realtime', 'historical')),
                captured_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS token_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                threshold_value REAL NOT NULL,
                threshold_unit TEXT NOT NULL CHECK(threshold_unit IN ('tokens', 'usd', 'percent')),
                time_window TEXT DEFAULT 'daily',
                is_enabled INTEGER DEFAULT 1,
                last_triggered_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_token_metrics_session ON token_metrics(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_token_metrics_model ON token_metrics(model)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_token_metrics_captured ON token_metrics(captured_at)")
        conn.commit()
        logger.info("Token tables initialized")


def init_tokens_router():
    """Initialize the tokens router - call at application startup."""
    ensure_tables_exist()


def read_last_lines(filepath: Path, num_lines: int = JSONL_TAIL_LINES) -> List[str]:
    """Read last N lines from file without loading entire file into memory."""
    lines = []
    try:
        with open(filepath, 'rb') as f:
            # Seek to end
            f.seek(0, 2)
            file_size = f.tell()
            if file_size == 0:
                return []

            # Read chunks from end
            chunk_size = 8192
            remaining = file_size
            buffer = b''

            while remaining > 0 and len(lines) < num_lines:
                read_size = min(chunk_size, remaining)
                remaining -= read_size
                f.seek(remaining)
                chunk = f.read(read_size)
                buffer = chunk + buffer

                # Split into lines
                split_lines = buffer.split(b'\n')
                if remaining > 0:
                    # Keep incomplete first line in buffer
                    buffer = split_lines[0]
                    lines = [l.decode('utf-8', errors='replace') for l in split_lines[1:] if l] + lines
                else:
                    lines = [l.decode('utf-8', errors='replace') for l in split_lines if l] + lines

            return lines[-num_lines:]
    except (OSError, UnicodeDecodeError) as e:
        logger.warning(f"Error reading last lines from {filepath}: {type(e).__name__}: {e}")
        return []


def parse_jsonl_for_tokens(project_dir: Path) -> List[Dict[str, Any]]:
    """Parse JSONL files for token usage data.

    Claude Code JSONL logs contain cumulative token usage in the 'lastModelUsage'
    field. The most recent entry with this field contains the final totals for
    the session, so we only need to find and process that one entry per file.

    We scan backwards from the end of the file to find the first valid entry
    with 'lastModelUsage', skipping empty lines and entries without usage data.
    """
    records = []
    if not project_dir.exists():
        return records

    for jsonl_file in project_dir.glob("*.jsonl"):
        try:
            lines = read_last_lines(jsonl_file, num_lines=JSONL_TAIL_LINES)
            if not lines:
                continue

            found_usage = False
            # Scan backwards through lines to find the most recent entry with usage data
            for line in reversed(lines):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "lastModelUsage" not in data:
                    continue

                # Found valid entry with cumulative usage - extract data
                session_id = data.get("sessionId", jsonl_file.stem)
                model_usage = data.get("lastModelUsage", {})
                timestamp = data.get("timestamp")

                for model, usage in model_usage.items():
                    records.append({
                        "session_id": session_id,
                        "project_path": str(project_dir),
                        "model": model,
                        "input_tokens": usage.get("inputTokens", 0),
                        "output_tokens": usage.get("outputTokens", 0),
                        "cache_read_tokens": usage.get("cacheReadInputTokens", 0),
                        "cache_creation_tokens": usage.get("cacheCreationInputTokens", 0),
                        "web_search_requests": usage.get("webSearchRequests", 0),
                        "cost_usd": usage.get("costUSD", 0.0),
                        "timestamp": timestamp
                    })
                found_usage = True
                break  # Only need the most recent entry (cumulative totals)

            if not found_usage:
                logger.debug(f"No token usage found in last {JSONL_TAIL_LINES} lines of {jsonl_file}")

        except Exception as e:
            logger.warning(f"Error parsing {jsonl_file}: {e}")
    return records


# Module-level cache for token usage data
_usage_cache: Optional[Dict[str, Any]] = None


def aggregate_sessions_by_model(sessions: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Aggregate session data by model. Reusable helper to avoid DRY violations."""
    by_model: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0,
                 "cache_creation_tokens": 0, "web_searches": 0, "cost_usd": 0.0, "session_count": 0}
    )
    for s in sessions:
        model = s["model"]
        by_model[model]["input_tokens"] += s["input_tokens"]
        by_model[model]["output_tokens"] += s["output_tokens"]
        by_model[model]["cache_read_tokens"] += s["cache_read_tokens"]
        by_model[model]["cache_creation_tokens"] += s["cache_creation_tokens"]
        by_model[model]["web_searches"] += s["web_search_requests"]
        by_model[model]["cost_usd"] += s["cost_usd"]
        by_model[model]["session_count"] += 1
    return dict(by_model)


def aggregate_totals(sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate total token counts across all sessions. Reusable helper for DRY."""
    total = {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0,
             "cache_creation_tokens": 0, "web_searches": 0, "cost_usd": 0.0}
    for s in sessions:
        total["input_tokens"] += s["input_tokens"]
        total["output_tokens"] += s["output_tokens"]
        total["cache_read_tokens"] += s["cache_read_tokens"]
        total["cache_creation_tokens"] += s["cache_creation_tokens"]
        total["web_searches"] += s["web_search_requests"]
        total["cost_usd"] += s["cost_usd"]
    return total


def compute_token_usage() -> Dict[str, Any]:
    """Compute token usage from JSONL files.

    Returns a dict with total, by_model, by_project, sessions list, and
    sessions_by_id dict for O(1) session lookups.
    """
    if not CLAUDE_PROJECTS_PATH.exists():
        return {
            "total": {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0,
                      "cache_creation_tokens": 0, "web_searches": 0, "cost_usd": 0.0},
            "by_model": {},
            "by_project": {},
            "sessions": [],
            "sessions_by_id": {}
        }

    all_records = []
    for project_dir in CLAUDE_PROJECTS_PATH.iterdir():
        if project_dir.is_dir():
            all_records.extend(parse_jsonl_for_tokens(project_dir))

    # Use shared helper for totals (DRY)
    total = aggregate_totals(all_records)

    by_project: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "session_count": 0}
    )

    # Build sessions_by_id for O(1) lookups and aggregate by_project
    sessions_by_id: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for record in all_records:
        project = record["project_path"]
        by_project[project]["input_tokens"] += record["input_tokens"]
        by_project[project]["output_tokens"] += record["output_tokens"]
        by_project[project]["cost_usd"] += record["cost_usd"]
        by_project[project]["session_count"] += 1

        # Index by session_id for O(1) lookups
        sessions_by_id[record["session_id"]].append(record)

    # Use shared helper for model aggregation
    by_model = aggregate_sessions_by_model(all_records)

    return {
        "total": total,
        "by_model": by_model,
        "by_project": dict(by_project),
        "sessions": all_records,
        "sessions_by_id": dict(sessions_by_id)
    }


def get_all_token_usage() -> Dict[str, Any]:
    """Get token usage with TTL-based caching to avoid repeated file parsing."""
    global _usage_cache, _cache_timestamp

    with _cache_lock:
        current_time = time.time()
        if _usage_cache is None or (current_time - _cache_timestamp) > _CACHE_TTL:
            _usage_cache = compute_token_usage()
            _cache_timestamp = current_time

        return _usage_cache


def invalidate_token_cache():
    """Invalidate the token usage cache (call after new data is added)."""
    global _usage_cache, _cache_timestamp
    with _cache_lock:
        _usage_cache = None
        _cache_timestamp = 0


@router.get("/current")
async def get_current_session_tokens(session_id: Optional[str] = Query(None)):
    """Get token usage for current or specified session."""
    ensure_tables_exist()
    # Note: get_all_token_usage() uses TTL-based caching (5 min) to avoid
    # repeated file parsing. For single-session lookups, caching provides
    # adequate performance. Future optimization could add session-specific queries.
    usage_data = get_all_token_usage()

    if not usage_data["sessions"]:
        return {"session_id": None, "project_path": None, "models": {}, "total_input_tokens": 0,
                "total_output_tokens": 0, "total_cost_usd": 0.0}

    if session_id:
        # O(1) lookup using sessions_by_id dict
        session_records = usage_data["sessions_by_id"].get(session_id, [])
    else:
        # Find latest session by timestamp using max() O(N) instead of sort O(N log N)
        # Filter to sessions with timestamps to avoid empty string comparison issues
        sessions_with_ts = [s for s in usage_data["sessions"] if s.get("timestamp")]
        if sessions_with_ts:
            latest_session = max(sessions_with_ts, key=lambda r: r["timestamp"])
            latest_session_id = latest_session["session_id"]
            session_records = usage_data["sessions_by_id"].get(latest_session_id, [])
        else:
            # If no sessions have timestamps, we cannot determine the latest one.
            # Return empty to trigger 404 - better than returning arbitrary session.
            session_records = []

    if not session_records:
        raise HTTPException(status_code=404, detail="Session not found")

    # Use defaultdict to avoid if-check on each iteration
    models: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"input_tokens": 0, "output_tokens": 0,
                 "cache_read_tokens": 0, "cache_creation_tokens": 0, "cost_usd": 0.0}
    )
    total_input = total_output = 0
    total_cost = 0.0

    for record in session_records:
        model = record["model"]
        models[model]["input_tokens"] += record["input_tokens"]
        models[model]["output_tokens"] += record["output_tokens"]
        models[model]["cache_read_tokens"] += record["cache_read_tokens"]
        models[model]["cache_creation_tokens"] += record["cache_creation_tokens"]
        models[model]["cost_usd"] += record["cost_usd"]
        total_input += record["input_tokens"]
        total_output += record["output_tokens"]
        total_cost += record["cost_usd"]

    return {"session_id": session_records[0]["session_id"],
            "project_path": session_records[0]["project_path"],
            "models": dict(models), "total_input_tokens": total_input,
            "total_output_tokens": total_output, "total_cost_usd": round(total_cost, 6)}


def _filter_sessions_by_days(sessions: List[Dict[str, Any]], days: int) -> List[Dict[str, Any]]:
    """Filter sessions to only include those within the specified number of days.

    Uses UTC timezone-aware datetimes for consistent cross-timezone comparisons.

    Args:
        sessions: List of session records to filter.
        days: Number of days to look back:
              - days < 0: no time-based filtering, returns all sessions
              - days = 0: returns sessions from today (since midnight UTC)
              - days > 0: returns sessions from the last N days

    Returns:
        Filtered list of sessions within the time window, or all sessions if days < 0.
    """
    if days < 0:
        return sessions

    # Use timezone-aware UTC datetime for consistent comparison
    if days == 0:
        # Today only: midnight UTC today
        now = datetime.now(timezone.utc)
        cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    filtered = []
    for s in sessions:
        ts = s.get("timestamp")
        if ts:
            # Parse timestamp to datetime for reliable comparison across formats
            try:
                session_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if session_dt >= cutoff:
                    filtered.append(s)
            except (ValueError, TypeError) as e:
                # Log unparseable timestamps for debugging, but don't fail the request
                logger.debug(f"Skipping session {s.get('session_id', 'unknown')}: unparseable timestamp '{ts}': {e}")
        # Exclude sessions without timestamp - cannot verify they fall within time window

    return filtered


@router.get("/summary")
async def get_token_summary(days: int = Query(30), project: Optional[str] = Query(None)):
    """Get aggregated token summary across all sessions."""
    ensure_tables_exist()
    usage_data = get_all_token_usage()

    # Filter by days first
    filtered_sessions = _filter_sessions_by_days(usage_data["sessions"], days)

    # Then filter by project if specified (match against project directory name)
    # Use Path().name for cross-platform compatibility (Windows uses backslashes)
    if project:
        filtered_sessions = [s for s in filtered_sessions
                             if Path(s["project_path"]).name == project]

    # Use shared helpers for aggregation (DRY)
    total = aggregate_totals(filtered_sessions)
    by_model = aggregate_sessions_by_model(filtered_sessions)

    return {"period_days": days,
            "total_input_tokens": total["input_tokens"],
            "total_output_tokens": total["output_tokens"],
            "total_cache_read_tokens": total["cache_read_tokens"],
            "total_cache_creation_tokens": total["cache_creation_tokens"],
            "total_web_searches": total["web_searches"],
            "total_cost_usd": round(total["cost_usd"], 2),
            "session_count": len(filtered_sessions),
            "model_breakdown": by_model}


@router.get("/models")
async def get_model_breakdown():
    """Get token usage breakdown by model."""
    ensure_tables_exist()
    usage_data = get_all_token_usage()
    models = []
    for model, data in usage_data["by_model"].items():
        total_tokens = data["input_tokens"] + data["output_tokens"]
        # Check before division to avoid division by zero
        if data["input_tokens"] > 0:
            cache_efficiency = (data["cache_read_tokens"] / data["input_tokens"]) * 100
        else:
            cache_efficiency = 0.0
        if data["session_count"] > 0:
            avg_cost = data["cost_usd"] / data["session_count"]
        else:
            avg_cost = 0.0
        models.append({
            "model": model,
            "input_tokens": data["input_tokens"],
            "output_tokens": data["output_tokens"],
            "total_tokens": total_tokens,
            "cache_read_tokens": data["cache_read_tokens"],
            "cache_creation_tokens": data["cache_creation_tokens"],
            "cache_efficiency_percent": round(cache_efficiency, 1),
            "web_searches": data["web_searches"],
            "cost_usd": round(data["cost_usd"], 4),
            "session_count": data["session_count"],
            "avg_cost_per_session": round(avg_cost, 4)
        })
    models.sort(key=lambda x: x["cost_usd"], reverse=True)
    return {"models": models, "total_models": len(models)}


@router.get("/projects")
async def get_project_breakdown():
    """Get token usage breakdown by project."""
    ensure_tables_exist()
    usage_data = get_all_token_usage()
    projects = []
    for project_path, data in usage_data["by_project"].items():
        projects.append({"project_path": project_path, "project_name": Path(project_path).name,
                         "input_tokens": data["input_tokens"], "output_tokens": data["output_tokens"],
                         "total_tokens": data["input_tokens"] + data["output_tokens"],
                         "cost_usd": round(data["cost_usd"], 4), "session_count": data["session_count"]})
    projects.sort(key=lambda x: x["cost_usd"], reverse=True)
    return {"projects": projects, "total_projects": len(projects)}


@router.get("/stats")
async def get_token_stats():
    """Get quick token usage statistics for dashboard display."""
    ensure_tables_exist()
    usage_data = get_all_token_usage()
    total_tokens = usage_data["total"]["input_tokens"] + usage_data["total"]["output_tokens"]
    return {"total_tokens": total_tokens,
            "total_cost_usd": round(usage_data["total"]["cost_usd"], 2),
            "input_tokens": usage_data["total"]["input_tokens"],
            "output_tokens": usage_data["total"]["output_tokens"],
            "cache_read_tokens": usage_data["total"]["cache_read_tokens"],
            "cache_creation_tokens": usage_data["total"]["cache_creation_tokens"],
            "web_searches": usage_data["total"]["web_searches"],
            "session_count": len(usage_data["sessions"]),
            "model_count": len(usage_data["by_model"]),
            "project_count": len(usage_data["by_project"])}


@router.get("/alerts")
async def list_alerts():
    """List all token usage alerts."""
    ensure_tables_exist()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, alert_type, threshold_value, threshold_unit, time_window, is_enabled, last_triggered_at, created_at FROM token_alerts ORDER BY created_at DESC")
        alerts = [dict_from_row(r) for r in cursor.fetchall()]
    return {"alerts": alerts, "count": len(alerts)}


@router.post("/alerts")
async def create_alert(alert: TokenAlertCreate):
    """Create a new token usage alert."""
    ensure_tables_exist()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO token_alerts (alert_type, threshold_value, threshold_unit, time_window, is_enabled) VALUES (?, ?, ?, ?, ?)",
                       (alert.alert_type, alert.threshold_value, alert.threshold_unit, alert.time_window, 1 if alert.is_enabled else 0))
        conn.commit()
        alert_id = cursor.lastrowid
    return {"id": alert_id, "message": "Alert created successfully"}


@router.put("/alerts/{alert_id}")
async def update_alert(alert_id: int, alert: TokenAlertUpdate):
    """Update an existing token usage alert."""
    ensure_tables_exist()

    # Use Pydantic's model_dump to get only set fields
    update_data = alert.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Validate fields against whitelist to prevent SQL injection via column names.
    # While Pydantic model fields are predefined, this explicit check ensures safety
    # if the model is modified and guards against any potential manipulation.
    invalid_fields = [f for f in update_data if f not in ALERT_UPDATE_ALLOWED_FIELDS]
    if invalid_fields:
        raise HTTPException(status_code=400, detail=f"Invalid fields for update: {invalid_fields}")

    # Convert is_enabled to integer for SQLite
    if "is_enabled" in update_data:
        update_data["is_enabled"] = 1 if update_data["is_enabled"] else 0

    # Build dynamic update query using only validated field names.
    # SECURITY: Field names are safe to interpolate because:
    # 1. They're validated against ALERT_UPDATE_ALLOWED_FIELDS whitelist above
    # 2. Values use parameterized placeholders (?) - never interpolated
    set_clauses = [f"{field} = ?" for field in update_data.keys()]
    values = list(update_data.values())
    values.append(alert_id)

    with get_db() as conn:
        cursor = conn.cursor()
        query = f"UPDATE token_alerts SET {', '.join(set_clauses)} WHERE id = ?"
        cursor.execute(query, values)
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Alert not found")
    return {"id": alert_id, "message": "Alert updated successfully"}


@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: int):
    """Delete a token usage alert."""
    ensure_tables_exist()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM token_alerts WHERE id = ?", (alert_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Alert not found")
    return {"id": alert_id, "message": "Alert deleted successfully"}
