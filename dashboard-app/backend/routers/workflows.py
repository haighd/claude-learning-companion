"""
Workflows Router - Workflow management and Kanban board.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter

from models import (
    WorkflowCreate,
    ActionResult,
    KanbanTaskCreate,
    KanbanTaskUpdate,
    KanbanTaskStatusUpdate,
)
from utils import get_db, dict_from_row

router = APIRouter(prefix="/api", tags=["workflows"])
logger = logging.getLogger(__name__)

# Path will be set from main.py
CLC_PATH = None

# Valid Kanban statuses
KANBAN_STATUSES = ["pending", "in_progress", "review", "done"]


def set_paths(clc_path: Path):
    """Set the paths for workflow operations."""
    global CLC_PATH
    CLC_PATH = clc_path


@router.get("/workflows")
async def get_workflows():
    """Get all workflow definitions."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT w.*, COUNT(DISTINCT we.id) as edge_count
            FROM workflows w
            LEFT JOIN workflow_edges we ON w.id = we.workflow_id
            GROUP BY w.id
            ORDER BY w.created_at DESC
        """)
        return [dict_from_row(r) for r in cursor.fetchall()]


@router.post("/workflows")
async def create_workflow(workflow: WorkflowCreate) -> ActionResult:
    """Create a new workflow."""
    try:
        if CLC_PATH is None:
            return ActionResult(success=False, message="Paths not configured")

        sys.path.insert(0, str(CLC_PATH / "conductor"))
        from conductor import Conductor

        conductor = Conductor()
        workflow_id = conductor.create_workflow(
            name=workflow.name,
            description=workflow.description,
            nodes=workflow.nodes,
            edges=workflow.edges
        )

        return ActionResult(
            success=True,
            message=f"Created workflow '{workflow.name}'",
            data={"workflow_id": workflow_id}
        )
    except Exception as e:
        logger.error(f"Error creating workflow '{workflow.name}': {e}", exc_info=True)
        return ActionResult(success=False, message="Failed to create workflow. Please check workflow configuration.")


# ==================== KANBAN BOARD ENDPOINTS ====================


@router.get("/kanban/tasks")
async def get_kanban_tasks():
    """Get all Kanban tasks grouped by status."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM kanban_tasks
            ORDER BY priority DESC, created_at ASC
        """)
        tasks = [dict_from_row(r) for r in cursor.fetchall()]

        # Parse JSON fields
        for task in tasks:
            task["linked_learnings"] = json.loads(task.get("linked_learnings") or "[]")
            task["linked_heuristics"] = json.loads(task.get("linked_heuristics") or "[]")
            task["tags"] = json.loads(task.get("tags") or "[]")

        # Group by status
        grouped = {status: [] for status in KANBAN_STATUSES}
        for task in tasks:
            status = task.get("status", "pending")
            if status in grouped:
                grouped[status].append(task)

        return {
            "tasks": tasks,
            "grouped": grouped,
            "statuses": KANBAN_STATUSES
        }


@router.post("/kanban/tasks")
async def create_kanban_task(task: KanbanTaskCreate) -> ActionResult:
    """Create a new Kanban task."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO kanban_tasks (title, description, status, priority, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                task.title,
                task.description,
                task.status or "pending",
                task.priority or 0,
                json.dumps(task.tags or []),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            task_id = cursor.lastrowid
            conn.commit()

            return ActionResult(
                success=True,
                message=f"Created task '{task.title}'",
                data={"task_id": task_id}
            )
    except Exception as e:
        logger.error(f"Error creating Kanban task: {e}", exc_info=True)
        return ActionResult(success=False, message=f"Failed to create task: {str(e)}")


@router.get("/kanban/tasks/{task_id}")
async def get_kanban_task(task_id: int):
    """Get a single Kanban task by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM kanban_tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if not row:
            return {"error": "Task not found"}
        task = dict_from_row(row)
        task["linked_learnings"] = json.loads(task.get("linked_learnings") or "[]")
        task["linked_heuristics"] = json.loads(task.get("linked_heuristics") or "[]")
        task["tags"] = json.loads(task.get("tags") or "[]")
        return task


@router.patch("/kanban/tasks/{task_id}")
async def update_kanban_task(task_id: int, update: KanbanTaskUpdate) -> ActionResult:
    """Update a Kanban task."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # Build update query dynamically
            updates = []
            values = []

            if update.title is not None:
                updates.append("title = ?")
                values.append(update.title)
            if update.description is not None:
                updates.append("description = ?")
                values.append(update.description)
            if update.status is not None:
                if update.status not in KANBAN_STATUSES:
                    return ActionResult(success=False, message=f"Invalid status. Must be one of: {KANBAN_STATUSES}")
                updates.append("status = ?")
                values.append(update.status)
                # Set completed_at if moving to done
                if update.status == "done":
                    updates.append("completed_at = ?")
                    values.append(datetime.now().isoformat())
            if update.priority is not None:
                updates.append("priority = ?")
                values.append(update.priority)
            if update.tags is not None:
                updates.append("tags = ?")
                values.append(json.dumps(update.tags))
            if update.linked_learnings is not None:
                updates.append("linked_learnings = ?")
                values.append(json.dumps(update.linked_learnings))
            if update.linked_heuristics is not None:
                updates.append("linked_heuristics = ?")
                values.append(json.dumps(update.linked_heuristics))

            if not updates:
                return ActionResult(success=False, message="No updates provided")

            updates.append("updated_at = ?")
            values.append(datetime.now().isoformat())
            values.append(task_id)

            cursor.execute(f"""
                UPDATE kanban_tasks
                SET {", ".join(updates)}
                WHERE id = ?
            """, values)
            conn.commit()

            if cursor.rowcount == 0:
                return ActionResult(success=False, message="Task not found")

            return ActionResult(success=True, message="Task updated")
    except Exception as e:
        logger.error(f"Error updating Kanban task {task_id}: {e}", exc_info=True)
        return ActionResult(success=False, message=f"Failed to update task: {str(e)}")


@router.patch("/kanban/tasks/{task_id}/status")
async def update_kanban_task_status(task_id: int, update: KanbanTaskStatusUpdate) -> ActionResult:
    """Move a task to a different column (update status)."""
    if update.status not in KANBAN_STATUSES:
        return ActionResult(success=False, message=f"Invalid status. Must be one of: {KANBAN_STATUSES}")

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            completed_at = datetime.now().isoformat() if update.status == "done" else None

            cursor.execute("""
                UPDATE kanban_tasks
                SET status = ?, updated_at = ?, completed_at = COALESCE(?, completed_at)
                WHERE id = ?
            """, (update.status, datetime.now().isoformat(), completed_at, task_id))
            conn.commit()

            if cursor.rowcount == 0:
                return ActionResult(success=False, message="Task not found")

            return ActionResult(success=True, message=f"Task moved to {update.status}")
    except Exception as e:
        logger.error(f"Error updating task status: {e}", exc_info=True)
        return ActionResult(success=False, message=f"Failed to update status: {str(e)}")


@router.delete("/kanban/tasks/{task_id}")
async def delete_kanban_task(task_id: int) -> ActionResult:
    """Delete a Kanban task."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM kanban_tasks WHERE id = ?", (task_id,))
            conn.commit()

            if cursor.rowcount == 0:
                return ActionResult(success=False, message="Task not found")

            return ActionResult(success=True, message="Task deleted")
    except Exception as e:
        logger.error(f"Error deleting Kanban task {task_id}: {e}", exc_info=True)
        return ActionResult(success=False, message=f"Failed to delete task: {str(e)}")


@router.post("/kanban/tasks/{task_id}/link")
async def link_task_to_learning(task_id: int, learning_id: str) -> ActionResult:
    """Link a Kanban task to a learning or heuristic."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # Get current linked learnings
            cursor.execute("SELECT linked_learnings FROM kanban_tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                return ActionResult(success=False, message="Task not found")

            linked = json.loads(row[0] or "[]")
            if learning_id not in linked:
                linked.append(learning_id)

            cursor.execute("""
                UPDATE kanban_tasks
                SET linked_learnings = ?, updated_at = ?
                WHERE id = ?
            """, (json.dumps(linked), datetime.now().isoformat(), task_id))
            conn.commit()

            return ActionResult(success=True, message=f"Linked learning {learning_id} to task")
    except Exception as e:
        logger.error(f"Error linking task to learning: {e}", exc_info=True)
        return ActionResult(success=False, message=f"Failed to link: {str(e)}")


@router.get("/kanban/stats")
async def get_kanban_stats():
    """
    Get Kanban task statistics including auto-creation breakdown.

    Returns counts by:
    - Auto-created vs manual
    - Source type (failure, CEO inbox, heuristic)
    - Status (pending, in_progress, review, done)
    """
    try:
        # Try importing kanban_automation for detailed stats
        try:
            clc_path = Path.home() / ".claude" / "clc"
            if str(clc_path) not in sys.path:
                sys.path.insert(0, str(clc_path))
            from memory.kanban_automation import get_auto_creation_stats
            return get_auto_creation_stats()
        except ImportError:
            # Fallback: calculate stats directly
            with get_db() as conn:
                cursor = conn.cursor()

                # Basic counts
                cursor.execute("SELECT COUNT(*) FROM kanban_tasks WHERE auto_created = 1")
                auto_total = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM kanban_tasks WHERE auto_created = 0")
                manual_total = cursor.fetchone()[0]

                return {
                    'auto_created_total': auto_total,
                    'manually_created_total': manual_total,
                    'failures_pending': 0,
                    'ceo_decisions_pending': 0,
                    'validations_pending': 0
                }
    except Exception as e:
        logger.error(f"Error getting Kanban stats: {e}", exc_info=True)
        return {
            'auto_created_total': 0,
            'manually_created_total': 0,
            'failures_pending': 0,
            'ceo_decisions_pending': 0,
            'validations_pending': 0
        }
