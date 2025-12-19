#!/usr/bin/env python3
"""
Graph Sync: Synchronize SQLite data with FalkorDB graph.

Maintains consistency between:
- SQLite: Primary store for structured data
- FalkorDB: Secondary store for relationships and semantic queries

Part of the Auto-Claude Integration (P3: Graph-Based Memory).
"""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from graph_store import get_graph_store, GraphStore

logger = logging.getLogger(__name__)

# Paths
CLC_PATH = Path.home() / ".claude" / "clc"
DB_PATH = CLC_PATH / "memory" / "index.db"


class GraphSync:
    """
    Synchronizes SQLite data with FalkorDB graph.

    Handles:
    - Initial sync of existing data
    - Incremental sync of new/updated records
    - Relationship detection and creation
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.graph = get_graph_store()
        self._last_sync: Optional[datetime] = None

    def get_db_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def full_sync(self) -> Dict:
        """
        Perform a full sync of all data from SQLite to graph.

        Returns:
            Dict with sync statistics
        """
        if not self.graph.is_available:
            logger.warning("Graph database not available, skipping sync")
            return {'status': 'skipped', 'reason': 'graph_unavailable'}

        stats = {
            'heuristics': 0,
            'golden_rules': 0,
            'domains': 0,
            'relationships': 0,
            'errors': []
        }

        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            # Sync heuristics
            cursor.execute("""
                SELECT id, rule, explanation, domain, confidence, is_golden
                FROM heuristics
                WHERE rule IS NOT NULL
            """)

            for row in cursor.fetchall():
                try:
                    if row['is_golden']:
                        self.graph.create_golden_rule_node(
                            row['id'],
                            row['rule'],
                            row['domain'] or 'general'
                        )
                        stats['golden_rules'] += 1
                    else:
                        self.graph.create_heuristic_node(
                            row['id'],
                            row['rule'],
                            row['domain'] or 'general',
                            row['confidence'] or 0.5
                        )
                        stats['heuristics'] += 1
                except Exception as e:
                    stats['errors'].append(f"Heuristic {row['id']}: {e}")

            # Sync learnings (failures and successes)
            cursor.execute("""
                SELECT id, type, title, summary, domain
                FROM learnings
                WHERE type IN ('failure', 'success')
            """)

            for row in cursor.fetchall():
                try:
                    if row['type'] == 'failure':
                        self.graph.create_failure_node(
                            f"learning_{row['id']}",
                            row['title'] or row['summary'] or '',
                            row['summary']
                        )
                    elif row['type'] == 'success':
                        self.graph.create_success_node(
                            f"learning_{row['id']}",
                            row['title'] or row['summary'] or '',
                            row['summary']
                        )
                except Exception as e:
                    stats['errors'].append(f"Learning {row['id']}: {e}")

            # Get unique domains
            cursor.execute("SELECT DISTINCT domain FROM heuristics WHERE domain IS NOT NULL")
            domains = [row['domain'] for row in cursor.fetchall()]
            stats['domains'] = len(domains)

            conn.close()

            self._last_sync = datetime.now()
            logger.info(f"Full sync completed: {stats}")

            return {
                'status': 'success',
                'stats': stats,
                'timestamp': self._last_sync.isoformat()
            }

        except Exception as e:
            logger.error(f"Error during full sync: {e}")
            return {'status': 'error', 'error': str(e)}

    def sync_heuristic(self, heuristic_id: int) -> bool:
        """
        Sync a single heuristic to the graph.

        Args:
            heuristic_id: ID of the heuristic to sync

        Returns:
            True if sync successful
        """
        if not self.graph.is_available:
            return False

        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, rule, explanation, domain, confidence, is_golden
                FROM heuristics
                WHERE id = ?
            """, (heuristic_id,))

            row = cursor.fetchone()
            conn.close()

            if not row:
                return False

            if row['is_golden']:
                return self.graph.create_golden_rule_node(
                    row['id'],
                    row['rule'],
                    row['domain'] or 'general'
                )
            else:
                return self.graph.create_heuristic_node(
                    row['id'],
                    row['rule'],
                    row['domain'] or 'general',
                    row['confidence'] or 0.5
                )

        except Exception as e:
            logger.error(f"Error syncing heuristic {heuristic_id}: {e}")
            return False

    def sync_learning(self, learning_id: int) -> bool:
        """
        Sync a single learning to the graph.

        Args:
            learning_id: ID of the learning to sync

        Returns:
            True if sync successful
        """
        if not self.graph.is_available:
            return False

        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, type, title, summary, domain
                FROM learnings
                WHERE id = ?
            """, (learning_id,))

            row = cursor.fetchone()
            conn.close()

            if not row:
                return False

            node_id = f"learning_{row['id']}"

            if row['type'] == 'failure':
                return self.graph.create_failure_node(
                    node_id,
                    row['title'] or row['summary'] or '',
                    row['summary']
                )
            elif row['type'] == 'success':
                return self.graph.create_success_node(
                    node_id,
                    row['title'] or row['summary'] or '',
                    row['summary']
                )

            return False

        except Exception as e:
            logger.error(f"Error syncing learning {learning_id}: {e}")
            return False

    def link_heuristic_to_failure(self, heuristic_id: int, failure_id: int) -> bool:
        """Link a heuristic to its source failure."""
        return self.graph.add_derived_from(heuristic_id, f"learning_{failure_id}")

    def link_heuristic_to_success(self, heuristic_id: int, success_id: int) -> bool:
        """Link a heuristic to a validating success."""
        return self.graph.add_validated_by(heuristic_id, f"learning_{success_id}")

    def mark_promoted(self, golden_rule_id: int, source_heuristic_id: int) -> bool:
        """Record that a golden rule was promoted from a heuristic."""
        return self.graph.add_promoted_from(golden_rule_id, source_heuristic_id)

    def incremental_sync(self, since: datetime = None) -> Dict:
        """
        Sync records modified since the given timestamp.

        Args:
            since: Only sync records modified after this time

        Returns:
            Dict with sync statistics
        """
        if not self.graph.is_available:
            return {'status': 'skipped', 'reason': 'graph_unavailable'}

        since = since or self._last_sync
        if not since:
            # If no last sync, do full sync
            return self.full_sync()

        stats = {
            'heuristics_synced': 0,
            'learnings_synced': 0,
            'errors': []
        }

        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            # Sync updated heuristics
            cursor.execute("""
                SELECT id FROM heuristics
                WHERE updated_at > ?
            """, (since.isoformat(),))

            for row in cursor.fetchall():
                if self.sync_heuristic(row['id']):
                    stats['heuristics_synced'] += 1

            # Sync updated learnings
            cursor.execute("""
                SELECT id FROM learnings
                WHERE updated_at > ?
            """, (since.isoformat(),))

            for row in cursor.fetchall():
                if self.sync_learning(row['id']):
                    stats['learnings_synced'] += 1

            conn.close()

            self._last_sync = datetime.now()

            return {
                'status': 'success',
                'stats': stats,
                'since': since.isoformat(),
                'timestamp': self._last_sync.isoformat()
            }

        except Exception as e:
            logger.error(f"Error during incremental sync: {e}")
            return {'status': 'error', 'error': str(e)}

    def get_sync_status(self) -> Dict:
        """Get the current sync status."""
        return {
            'graph_available': self.graph.is_available,
            'last_sync': self._last_sync.isoformat() if self._last_sync else None,
            'graph_stats': self.graph.get_graph_stats()
        }


# Singleton instance
_sync_service: Optional[GraphSync] = None


def get_sync_service() -> GraphSync:
    """Get the singleton sync service instance."""
    global _sync_service
    if _sync_service is None:
        _sync_service = GraphSync()
    return _sync_service


def sync_on_startup():
    """Perform initial sync on application startup."""
    service = get_sync_service()
    if service.graph.is_available:
        logger.info("Performing initial graph sync...")
        result = service.full_sync()
        logger.info(f"Initial sync result: {result['status']}")
        return result
    else:
        logger.info("Graph database not available, skipping initial sync")
        return {'status': 'skipped', 'reason': 'graph_unavailable'}


# For testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    service = get_sync_service()
    print(f"Sync status: {service.get_sync_status()}")

    if service.graph.is_available:
        result = service.full_sync()
        print(f"Sync result: {result}")
    else:
        print("Graph database not available")
        print("Start FalkorDB with: docker-compose up -d")
