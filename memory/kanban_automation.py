"""
Kanban Task Automation Module for the Emergent Learning Framework.

Automatically creates and manages Kanban tasks based on:
- Failures captured by the learning system
- CEO inbox items requiring decisions
- Heuristics requiring validation

This provides automatic task generation and linking between
the learning system and the Kanban board.
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

# Database path
CLC_PATH = Path.home() / ".claude" / "clc"
DB_PATH = CLC_PATH / "memory" / "index.db"

logger = logging.getLogger(__name__)


def get_db():
    """Get database connection with timeout."""
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def create_task_from_failure(
    learning_id: int,
    title: str,
    summary: str,
    domain: str = "general"
) -> Optional[int]:
    """
    Create a Kanban task from a captured failure.

    Args:
        learning_id: ID of the learning record (failure)
        title: Task title
        summary: Task description
        domain: Domain of the failure

    Returns:
        Task ID if successful, None on error
    """
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Check if task already exists for this learning
        cursor.execute("""
            SELECT id FROM kanban_tasks
            WHERE auto_source = 'failure' AND source_id = ?
        """, (str(learning_id),))

        existing = cursor.fetchone()
        if existing:
            logger.debug(f"Task already exists for failure {learning_id}: {existing['id']}")
            conn.close()
            return existing['id']

        # Create new task
        cursor.execute("""
            INSERT INTO kanban_tasks (
                title, description, status, priority, tags,
                linked_learnings, auto_created, auto_source, source_id,
                created_at, updated_at
            )
            VALUES (?, ?, 'pending', 1, ?, ?, 1, 'failure', ?, ?, ?)
        """, (
            title,
            summary,
            json.dumps([domain]),
            json.dumps([learning_id]),
            str(learning_id),
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))

        task_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Created Kanban task {task_id} from failure {learning_id}")
        return task_id

    except Exception as e:
        logger.error(f"Failed to create task from failure {learning_id}: {e}")
        return None


def create_task_from_ceo_inbox(
    filepath: str,
    title: str,
    priority: int = 2
) -> Optional[int]:
    """
    Create a Kanban task from a CEO inbox item.

    Args:
        filepath: Path to the CEO inbox markdown file
        title: Task title from the file
        priority: Priority level (default: 2 for high)

    Returns:
        Task ID if successful, None on error
    """
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Check if task already exists for this file
        cursor.execute("""
            SELECT id FROM kanban_tasks
            WHERE auto_source = 'ceo_inbox' AND source_id = ?
        """, (filepath,))

        existing = cursor.fetchone()
        if existing:
            logger.debug(f"Task already exists for CEO inbox {filepath}: {existing['id']}")
            conn.close()
            return existing['id']

        # Read file content for description
        file_path = CLC_PATH / filepath
        description = f"CEO decision needed: {filepath}"
        if file_path.exists():
            try:
                content = file_path.read_text()
                # Extract first paragraph as description
                lines = [line.strip() for line in content.split('\n') if line.strip()]
                if len(lines) > 2:
                    description = lines[2][:200]  # Third line, first 200 chars
            except Exception as e:
                logger.warning(f"Could not read CEO inbox file {filepath}: {e}")

        # Create new task
        cursor.execute("""
            INSERT INTO kanban_tasks (
                title, description, status, priority, tags,
                auto_created, auto_source, source_id,
                created_at, updated_at
            )
            VALUES (?, ?, 'pending', ?, ?, 1, 'ceo_inbox', ?, ?, ?)
        """, (
            title,
            description,
            priority,
            json.dumps(['ceo-decision']),
            filepath,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))

        task_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Created Kanban task {task_id} from CEO inbox {filepath}")
        return task_id

    except Exception as e:
        logger.error(f"Failed to create task from CEO inbox {filepath}: {e}")
        return None


def create_task_from_heuristic(
    heuristic_id: int,
    rule: str,
    domain: str = "general"
) -> Optional[int]:
    """
    Create a Kanban task for heuristic validation.

    Args:
        heuristic_id: ID of the heuristic
        rule: The heuristic rule text
        domain: Domain of the heuristic

    Returns:
        Task ID if successful, None on error
    """
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Check if task already exists for this heuristic
        cursor.execute("""
            SELECT id FROM kanban_tasks
            WHERE auto_source = 'heuristic' AND source_id = ?
        """, (str(heuristic_id),))

        existing = cursor.fetchone()
        if existing:
            logger.debug(f"Task already exists for heuristic {heuristic_id}: {existing['id']}")
            conn.close()
            return existing['id']

        # Create validation task in 'review' status
        title = f"Validate heuristic: {rule[:50]}..."
        description = f"Review and validate heuristic #{heuristic_id}: {rule}"

        cursor.execute("""
            INSERT INTO kanban_tasks (
                title, description, status, priority, tags,
                linked_heuristics, auto_created, auto_source, source_id,
                created_at, updated_at
            )
            VALUES (?, ?, 'review', 1, ?, ?, 1, 'heuristic', ?, ?, ?)
        """, (
            title,
            description,
            json.dumps([domain, 'validation']),
            json.dumps([heuristic_id]),
            str(heuristic_id),
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))

        task_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Created Kanban task {task_id} for heuristic {heuristic_id}")
        return task_id

    except Exception as e:
        logger.error(f"Failed to create task from heuristic {heuristic_id}: {e}")
        return None


def move_task_to_done(task_id: int) -> bool:
    """
    Move a task to 'done' status.

    Args:
        task_id: ID of the task to complete

    Returns:
        True if successful, False on error
    """
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE kanban_tasks
            SET status = 'done',
                completed_at = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            task_id
        ))

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        if success:
            logger.info(f"Moved Kanban task {task_id} to done")
        else:
            logger.warning(f"Task {task_id} not found when trying to mark done")

        return success

    except Exception as e:
        logger.error(f"Failed to move task {task_id} to done: {e}")
        return False


def find_linked_task(
    learning_id: Optional[int] = None,
    heuristic_id: Optional[int] = None
) -> Optional[Dict]:
    """
    Find a Kanban task linked to a learning or heuristic.

    Args:
        learning_id: Learning ID to search for
        heuristic_id: Heuristic ID to search for

    Returns:
        Task dict if found, None otherwise
    """
    try:
        conn = get_db()
        cursor = conn.cursor()

        if learning_id is not None:
            cursor.execute("""
                SELECT * FROM kanban_tasks
                WHERE auto_source = 'failure' AND source_id = ?
                LIMIT 1
            """, (str(learning_id),))
        elif heuristic_id is not None:
            cursor.execute("""
                SELECT * FROM kanban_tasks
                WHERE auto_source = 'heuristic' AND source_id = ?
                LIMIT 1
            """, (str(heuristic_id),))
        else:
            conn.close()
            return None

        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    except Exception as e:
        logger.error(f"Failed to find linked task: {e}")
        return None


def get_auto_creation_stats() -> Dict[str, int]:
    """
    Get statistics on auto-created tasks.

    Returns:
        Dictionary with counts by source and status
    """
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Count by auto_source and status
        cursor.execute("""
            SELECT
                auto_source,
                status,
                COUNT(*) as count
            FROM kanban_tasks
            WHERE auto_created = 1
            GROUP BY auto_source, status
        """)

        results = cursor.fetchall()

        # Count manual tasks
        cursor.execute("""
            SELECT COUNT(*) FROM kanban_tasks WHERE auto_created = 0
        """)
        manual_count = cursor.fetchone()[0]

        conn.close()

        # Build stats dict
        stats = {
            'failures_pending': 0,
            'ceo_decisions_pending': 0,
            'validations_pending': 0,
            'auto_created_total': 0,
            'manually_created_total': manual_count
        }

        for row in results:
            source = row['auto_source'] or 'unknown'
            status = row['status']
            count = row['count']

            stats['auto_created_total'] += count

            if status == 'pending':
                if source == 'failure':
                    stats['failures_pending'] += count
                elif source == 'ceo_inbox':
                    stats['ceo_decisions_pending'] += count
            elif status == 'review':
                if source == 'heuristic':
                    stats['validations_pending'] += count

        return stats

    except Exception as e:
        logger.error(f"Failed to get auto-creation stats: {e}")
        return {
            'failures_pending': 0,
            'ceo_decisions_pending': 0,
            'validations_pending': 0,
            'auto_created_total': 0,
            'manually_created_total': 0
        }
