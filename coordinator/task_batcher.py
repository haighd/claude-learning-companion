#!/usr/bin/env python3
"""
Task Batcher: Context-aware task splitting and batching.

Part of Phase 3: Preventive Context Management.

Estimates token cost before task assignment, splits large tasks into
context-sized chunks, and groups related tasks into batches.

Usage:
    from coordinator.task_batcher import TaskBatcher

    batcher = TaskBatcher(project_root)
    batches = batcher.batch_tasks_by_context(tasks)
"""

import traceback
from pathlib import Path
from typing import Dict, List, Any, Set, Optional
import sys

# Use shared module loader utility
from utils.module_loader import get_module_attribute

_clc_root = Path(__file__).parent.parent

# Load context_monitor module
_context_monitor_path = _clc_root / "watcher" / "context_monitor.py"
get_context_status, HAS_CONTEXT_MONITOR = get_module_attribute(
    "context_monitor", _context_monitor_path, "get_context_status"
)

# Load dependency_graph module
_dep_graph_path = Path(__file__).parent / "dependency_graph.py"
DependencyGraph, HAS_DEPENDENCY_GRAPH = get_module_attribute(
    "dependency_graph", _dep_graph_path, "DependencyGraph"
)


# Token estimation constants (conservative)
CONTEXT_BUDGET = 200_000  # Total context window estimate
SAFETY_MARGIN = 0.4  # Reserve 40% for safety (use only 60%)
EFFECTIVE_BUDGET = int(CONTEXT_BUDGET * (1 - SAFETY_MARGIN))  # 120,000 tokens

# Task complexity multipliers
COMPLEXITY_KEYWORDS = {
    'refactor': 2.0,
    'implement': 1.5,
    'migrate': 2.0,
    'redesign': 2.5,
    'fix': 1.0,
    'update': 0.8,
    'add': 1.2,
    'remove': 0.7,
    'test': 1.3,
    'document': 0.6,
}

# Average token costs per operation type
TOKEN_COSTS = {
    'base_task': 500,           # Task description overhead
    'file_read': 4000,          # Average file read
    'file_edit': 3000,          # Average file edit
    'subagent_spawn': 10000,    # Subagent context
    'tool_call': 1000,          # Tool invocation
}

# Default number of subagents assumed when parallel work is detected
DEFAULT_SUBAGENT_COUNT = 2


class TaskBatcher:
    """Context-aware task batching and splitting."""

    def __init__(self, project_root: str = "."):
        """Initialize task batcher.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root).resolve()
        self._dep_graph = None
        self._graph_scanned = False

    @property
    def dep_graph(self) -> Optional[Any]:
        """Lazy-load dependency graph."""
        if self._dep_graph is None and HAS_DEPENDENCY_GRAPH:
            self._dep_graph = DependencyGraph(str(self.project_root))
        return self._dep_graph

    def _ensure_graph_scanned(self):
        """Ensure dependency graph is scanned."""
        if not self._graph_scanned and self.dep_graph is not None:
            try:
                self.dep_graph.scan()
                self._graph_scanned = True
            except (OSError, AttributeError):
                # OSError covers IOError (its alias in Python 3)
                # Non-fatal - continue without dependency analysis
                sys.stderr.write(f"Warning: Dependency graph scan failed:\n{traceback.format_exc()}\n")

    def estimate_task_tokens(self, task: Dict) -> int:
        """
        Estimate tokens a task will consume.

        Args:
            task: Task dict with 'task' description and optional metadata

        Returns:
            Estimated token count
        """
        description = task.get('task', '') or task.get('description', '')

        # Base cost from description length (~4 chars per token)
        base_cost = max(TOKEN_COSTS['base_task'], len(description) // 4)

        # Complexity multiplier from keywords
        multiplier = 1.0
        desc_lower = description.lower()
        for keyword, mult in COMPLEXITY_KEYWORDS.items():
            if keyword in desc_lower:
                multiplier = max(multiplier, mult)

        # File-based cost
        files = task.get('files', task.get('scope', []))
        if files:
            file_cost = len(files) * TOKEN_COSTS['file_read']
        else:
            # Estimate based on task description or default
            estimated_files = task.get('estimated_files', 3)
            file_cost = estimated_files * TOKEN_COSTS['file_read']

        # Subagent cost (if task suggests spawning agents)
        subagent_keywords = ['parallel', 'swarm', 'multiple agents', 'concurrently']
        subagent_cost = 0
        for kw in subagent_keywords:
            if kw in desc_lower:
                subagent_cost = TOKEN_COSTS['subagent_spawn'] * DEFAULT_SUBAGENT_COUNT
                break

        total = int((base_cost + file_cost + subagent_cost) * multiplier)
        return total

    def split_task_for_context(self, task: Dict, available_tokens: int) -> List[Dict]:
        """
        Split a large task into context-sized subtasks.

        Args:
            task: Task to potentially split
            available_tokens: Remaining context budget

        Returns:
            List of subtasks (possibly just [task] if it fits)
        """
        estimated = self.estimate_task_tokens(task)

        # If it fits, return as-is
        if estimated <= available_tokens:
            return [task]

        # If task has explicit subtasks, use those
        if 'subtasks' in task and task['subtasks']:
            return task['subtasks']

        # If task has files, split by file groups
        files = task.get('files', task.get('scope', []))
        if files and len(files) > 1:
            return self._split_by_file_groups(task, files)

        # Try using dependency graph to find related files
        self._ensure_graph_scanned()
        if files and self.dep_graph is not None:
            try:
                # Track files whose dependency clusters we've already processed to avoid
                # redundant get_cluster calls. Once a file is in a processed cluster,
                # we don't need to compute its cluster again since dependency clusters
                # are transitive.
                processed_files: Set[str] = set()
                for f in files:
                    # Skip files that are already part of previously computed clusters
                    # to avoid redundant cluster expansion work.
                    if f in processed_files:
                        continue
                    related = self.dep_graph.get_cluster(f, depth=1)
                    processed_files.update(related)
                if len(processed_files) > 1:
                    return self._split_by_file_groups(task, list(processed_files))
            except (AttributeError, TypeError, KeyError):
                # These exceptions can occur when:
                # - AttributeError: dep_graph methods unavailable or return unexpected types
                # - TypeError: get_cluster returns non-iterable or incompatible type
                # - KeyError: internal graph data structure missing expected keys
                sys.stderr.write(f"Warning: Failed to get dependency cluster for splitting task:\n{traceback.format_exc()}\n")
                # Fall through to return task with warning

        # Cannot split meaningfully - return with warning
        task_copy = dict(task)
        task_copy['warning'] = (
            f'Task may exceed context budget '
            f'({estimated:,} estimated > {available_tokens:,} available)'
        )
        return [task_copy]

    def _split_by_file_groups(self, task: Dict, files: List[str]) -> List[Dict]:
        """Split task by file groups that fit within budget."""
        # Early return for empty files - nothing to split
        if not files:
            return [task]

        self._ensure_graph_scanned()

        # Group files by dependency clusters
        clusters: List[List[str]] = []
        assigned: Set[str] = set()
        files_set = set(files)  # Convert once for efficient intersection

        for f in files:
            if f in assigned:
                continue

            if self.dep_graph is not None:
                try:
                    full_cluster = self.dep_graph.get_cluster(f, depth=1)
                    relevant_cluster = full_cluster.intersection(files_set)
                except (AttributeError, TypeError, KeyError):
                    # See split_task_for_context for exception rationale
                    sys.stderr.write(f"Warning: Failed to get dependency cluster for file group:\n{traceback.format_exc()}\n")
                    relevant_cluster = {f}
            else:
                relevant_cluster = {f}

            if relevant_cluster:
                clusters.append(list(relevant_cluster))
                assigned.update(relevant_cluster)
            else:
                clusters.append([f])
                assigned.add(f)

        # Create subtasks for each cluster
        subtasks = []
        base_desc = task.get('task', '') or task.get('description', '')

        for i, cluster_files in enumerate(clusters):
            subtask = {
                'id': f"{task.get('id', 'task')}-part-{i+1}",
                'task': f"[Part {i+1}/{len(clusters)}] {base_desc}",
                'files': cluster_files,
                'scope': cluster_files,
                'priority': task.get('priority', 5),
                'parent_task': task.get('id'),
                'part_number': i + 1,
                'total_parts': len(clusters),
            }
            subtasks.append(subtask)

        return subtasks

    def batch_tasks_by_context(self, tasks: List[Dict]) -> List[List[Dict]]:
        """
        Group tasks into batches that fit within context budget.

        Uses dependency graph for smart grouping - related files go together.

        Args:
            tasks: List of tasks to batch

        Returns:
            List of batches (each batch is a list of tasks)
        """
        if not tasks:
            return []

        # Get available tokens
        available = self.get_available_tokens()

        self._ensure_graph_scanned()
        batches: List[List[Dict]] = []
        current_batch: List[Dict] = []
        current_batch_tokens = 0

        # Sort tasks by priority (lower number = higher priority)
        sorted_tasks = sorted(tasks, key=lambda t: t.get('priority', 5))

        for task in sorted_tasks:
            estimated = self.estimate_task_tokens(task)

            # If task is too large, try to split it
            if estimated > available:
                subtasks = self.split_task_for_context(task, available)
                for subtask in subtasks:
                    sub_estimate = self.estimate_task_tokens(subtask)
                    if current_batch_tokens + sub_estimate > available:
                        if current_batch:
                            batches.append(current_batch)
                        current_batch = [subtask]
                        current_batch_tokens = sub_estimate
                    else:
                        current_batch.append(subtask)
                        current_batch_tokens += sub_estimate
            elif current_batch_tokens + estimated > available:
                # Start new batch
                if current_batch:
                    batches.append(current_batch)
                current_batch = [task]
                current_batch_tokens = estimated
            else:
                current_batch.append(task)
                current_batch_tokens += estimated

        # Don't forget the last batch
        if current_batch:
            batches.append(current_batch)

        return batches

    def get_available_tokens(self) -> int:
        """Get remaining tokens available for new work."""
        if HAS_CONTEXT_MONITOR and get_context_status is not None:
            try:
                status = get_context_status()
                current_usage = status.get('estimated_usage', 0.0)
                available = int(CONTEXT_BUDGET * (1.0 - current_usage))
                return available
            except (AttributeError, TypeError, KeyError):
                sys.stderr.write(
                    f"Warning: Failed to get context status for available tokens:\n"
                    f"{traceback.format_exc()}\n"
                )
                # Fall through to return fallback budget

        # Fallback to effective budget
        return EFFECTIVE_BUDGET


# CLI for testing
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Task Batcher CLI")
    parser.add_argument("command", choices=["estimate", "split", "batch", "available"],
                        help="Command to run")
    parser.add_argument("--task", help="Task description")
    parser.add_argument("--files", nargs="+", help="Files in scope")
    parser.add_argument("--project", default=".", help="Project root")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    batcher = TaskBatcher(args.project)

    if args.command == "estimate":
        task = {"task": args.task or "Example task", "files": args.files or []}
        tokens = batcher.estimate_task_tokens(task)
        if args.json:
            print(json.dumps({"estimated_tokens": tokens}))
        else:
            print(f"Estimated tokens: {tokens:,}")

    elif args.command == "available":
        available = batcher.get_available_tokens()
        if args.json:
            print(json.dumps({"available_tokens": available}))
        else:
            print(f"Available tokens: {available:,}")
            print(f"Context budget: {CONTEXT_BUDGET:,}")
            print(f"Effective budget (60%): {EFFECTIVE_BUDGET:,}")

    elif args.command == "split":
        task = {"task": args.task or "Example task", "files": args.files or []}
        available = batcher.get_available_tokens()
        subtasks = batcher.split_task_for_context(task, available)
        if args.json:
            print(json.dumps({"subtasks": subtasks}, indent=2))
        else:
            print(f"Split into {len(subtasks)} subtasks:")
            for i, st in enumerate(subtasks):
                desc = st.get('task', '')[:60]
                print(f"  {i+1}. {desc}...")

    elif args.command == "batch":
        # Create example tasks for batching demo
        if args.task:
            tasks = [{"task": args.task, "files": args.files or []}]
        else:
            tasks = [
                {"task": f"Implement feature {i}", "estimated_files": 3}
                for i in range(5)
            ]

        batches = batcher.batch_tasks_by_context(tasks)
        if args.json:
            print(json.dumps({"batches": batches}, indent=2))
        else:
            print(f"Created {len(batches)} batches:")
            for i, batch in enumerate(batches):
                total_tokens = sum(batcher.estimate_task_tokens(t) for t in batch)
                print(f"  Batch {i+1}: {len(batch)} tasks, ~{total_tokens:,} tokens")
