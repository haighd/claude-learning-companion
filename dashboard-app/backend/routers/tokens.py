"""
Tokens Router - Token accounting, usage tracking, cost analysis, and alerts.
"""

import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from utils import get_db, dict_from_row

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tokens", tags=["tokens"])

CLAUDE_PROJECTS_PATH = Path.home() / ".claude" / "projects"


class TokenAlertCreate(BaseModel):
    alert_type: str
    threshold_value: float
    threshold_unit: str
    time_window: str = "daily"
    is_enabled: bool = True


class TokenAlertUpdate(BaseModel):
    alert_type: Optional[str] = None
    threshold_value: Optional[float] = None
    threshold_unit: Optional[str] = None
    time_window: Optional[str] = None
    is_enabled: Optional[bool] = None


def ensure_tables_exist():
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
        conn.commit()


def parse_jsonl_for_tokens(project_dir: Path) -> List[Dict[str, Any]]:
    records = []
    if not project_dir.exists():
        return records

    for jsonl_file in project_dir.glob("*.jsonl"):
        try:
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            if not lines:
                continue

            for line in reversed(lines[-10:]):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "lastModelUsage" not in data:
                    continue

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
                break
        except Exception as e:
            logger.warning(f"Error parsing {jsonl_file}: {e}")
    return records


def get_all_token_usage() -> Dict[str, Any]:
    if not CLAUDE_PROJECTS_PATH.exists():
        return {
            "total": {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0,
                      "cache_creation_tokens": 0, "web_searches": 0, "cost_usd": 0.0},
            "by_model": {},
            "by_project": {},
            "sessions": []
        }

    all_records = []
    for project_dir in CLAUDE_PROJECTS_PATH.iterdir():
        if project_dir.is_dir():
            all_records.extend(parse_jsonl_for_tokens(project_dir))

    total = {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0,
             "cache_creation_tokens": 0, "web_searches": 0, "cost_usd": 0.0}
    by_model: Dict[str, Dict[str, Any]] = {}
    by_project: Dict[str, Dict[str, Any]] = {}

    for record in all_records:
        total["input_tokens"] += record["input_tokens"]
        total["output_tokens"] += record["output_tokens"]
        total["cache_read_tokens"] += record["cache_read_tokens"]
        total["cache_creation_tokens"] += record["cache_creation_tokens"]
        total["web_searches"] += record["web_search_requests"]
        total["cost_usd"] += record["cost_usd"]

        model = record["model"]
        if model not in by_model:
            by_model[model] = {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0,
                               "cache_creation_tokens": 0, "web_searches": 0, "cost_usd": 0.0, "session_count": 0}
        by_model[model]["input_tokens"] += record["input_tokens"]
        by_model[model]["output_tokens"] += record["output_tokens"]
        by_model[model]["cache_read_tokens"] += record["cache_read_tokens"]
        by_model[model]["cache_creation_tokens"] += record["cache_creation_tokens"]
        by_model[model]["web_searches"] += record["web_search_requests"]
        by_model[model]["cost_usd"] += record["cost_usd"]
        by_model[model]["session_count"] += 1

        project = record["project_path"]
        if project not in by_project:
            by_project[project] = {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "session_count": 0}
        by_project[project]["input_tokens"] += record["input_tokens"]
        by_project[project]["output_tokens"] += record["output_tokens"]
        by_project[project]["cost_usd"] += record["cost_usd"]
        by_project[project]["session_count"] += 1

    return {"total": total, "by_model": by_model, "by_project": by_project, "sessions": all_records}


@router.get("/current")
async def get_current_session_tokens(session_id: Optional[str] = Query(None)):
    """Get token usage for current or specified session."""
    ensure_tables_exist()
    usage_data = get_all_token_usage()

    if not usage_data["sessions"]:
        return {"session_id": None, "models": {}, "total_input_tokens": 0,
                "total_output_tokens": 0, "total_cost_usd": 0.0}

    if session_id:
        session_records = [r for r in usage_data["sessions"] if r["session_id"] == session_id]
    else:
        session_records = usage_data["sessions"][:1]

    if not session_records:
        raise HTTPException(status_code=404, detail="Session not found")

    models: Dict[str, Dict[str, Any]] = {}
    total_input = total_output = 0
    total_cost = 0.0

    for record in session_records:
        model = record["model"]
        if model not in models:
            models[model] = {"input_tokens": 0, "output_tokens": 0,
                            "cache_read_tokens": 0, "cache_creation_tokens": 0, "cost_usd": 0.0}
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
            "models": models, "total_input_tokens": total_input,
            "total_output_tokens": total_output, "total_cost_usd": round(total_cost, 6)}


@router.get("/summary")
async def get_token_summary(days: int = Query(30), project: Optional[str] = Query(None)):
    """Get aggregated token summary across all sessions."""
    ensure_tables_exist()
    usage_data = get_all_token_usage()

    if project:
        usage_data["sessions"] = [s for s in usage_data["sessions"] if project in s["project_path"]]
        usage_data["total"] = {
            "input_tokens": sum(s["input_tokens"] for s in usage_data["sessions"]),
            "output_tokens": sum(s["output_tokens"] for s in usage_data["sessions"]),
            "cache_read_tokens": sum(s["cache_read_tokens"] for s in usage_data["sessions"]),
            "cache_creation_tokens": sum(s["cache_creation_tokens"] for s in usage_data["sessions"]),
            "web_searches": sum(s["web_search_requests"] for s in usage_data["sessions"]),
            "cost_usd": sum(s["cost_usd"] for s in usage_data["sessions"])
        }

    return {"period_days": days,
            "total_input_tokens": usage_data["total"]["input_tokens"],
            "total_output_tokens": usage_data["total"]["output_tokens"],
            "total_cache_read_tokens": usage_data["total"]["cache_read_tokens"],
            "total_cache_creation_tokens": usage_data["total"]["cache_creation_tokens"],
            "total_web_searches": usage_data["total"]["web_searches"],
            "total_cost_usd": round(usage_data["total"]["cost_usd"], 2),
            "session_count": len(usage_data["sessions"]),
            "model_breakdown": usage_data["by_model"]}


@router.get("/models")
async def get_model_breakdown():
    """Get token usage breakdown by model."""
    ensure_tables_exist()
    usage_data = get_all_token_usage()
    models = []
    for model, data in usage_data["by_model"].items():
        total_tokens = data["input_tokens"] + data["output_tokens"]
        cache_eff = (data["cache_read_tokens"] / data["input_tokens"]) * 100 if data["input_tokens"] > 0 else 0.0
        models.append({"model": model, "input_tokens": data["input_tokens"],
                       "output_tokens": data["output_tokens"], "total_tokens": total_tokens,
                       "cache_read_tokens": data["cache_read_tokens"],
                       "cache_creation_tokens": data["cache_creation_tokens"],
                       "cache_efficiency_percent": round(cache_eff, 1),
                       "web_searches": data["web_searches"],
                       "cost_usd": round(data["cost_usd"], 4),
                       "session_count": data["session_count"],
                       "avg_cost_per_session": round(data["cost_usd"] / data["session_count"], 4) if data["session_count"] > 0 else 0})
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
    with get_db() as conn:
        cursor = conn.cursor()
        updates, values = [], []
        if alert.alert_type is not None:
            updates.append("alert_type = ?")
            values.append(alert.alert_type)
        if alert.threshold_value is not None:
            updates.append("threshold_value = ?")
            values.append(alert.threshold_value)
        if alert.threshold_unit is not None:
            updates.append("threshold_unit = ?")
            values.append(alert.threshold_unit)
        if alert.time_window is not None:
            updates.append("time_window = ?")
            values.append(alert.time_window)
        if alert.is_enabled is not None:
            updates.append("is_enabled = ?")
            values.append(1 if alert.is_enabled else 0)
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        values.append(alert_id)
        cursor.execute(f"UPDATE token_alerts SET {', '.join(updates)} WHERE id = ?", values)
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
