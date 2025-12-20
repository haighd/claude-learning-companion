#!/usr/bin/env python3
"""
Graph Sync Background Service.

Periodically synchronizes SQLite data to FalkorDB graph store.
Provides graceful degradation when FalkorDB is unavailable.
"""

import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add CLC to path
CLC_PATH = Path.home() / ".claude" / "clc"
if str(CLC_PATH) not in sys.path:
    sys.path.insert(0, str(CLC_PATH))

from memory.graph_sync import GraphSync

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GraphSyncService:
    """
    Background service for graph synchronization.

    Runs periodic syncs between SQLite and FalkorDB.
    """

    def __init__(self, sync_interval: int = 300, full_sync_on_startup: bool = True):
        """
        Initialize the sync service.

        Args:
            sync_interval: Seconds between syncs (default: 300 = 5 minutes)
            full_sync_on_startup: Perform full sync on startup (default: True)
        """
        self.sync_interval = sync_interval
        self.full_sync_on_startup = full_sync_on_startup
        self.running = False
        self.sync = GraphSync()
        self.stats = {
            'syncs_completed': 0,
            'syncs_failed': 0,
            'last_sync_time': None,
            'last_sync_duration': 0.0
        }

        # Register signal handlers
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()

    def run(self):
        """
        Start the sync service loop.
        """
        self.running = True
        logger.info(f"Graph Sync Service started: syncing every {self.sync_interval}s")

        # Initial sync on startup
        if self.full_sync_on_startup:
            logger.info("Performing initial full sync...")
            self._perform_sync(full=True)
        else:
            logger.info("Skipping initial full sync (will perform incremental sync)")

        # Main loop
        while self.running:
            try:
                time.sleep(self.sync_interval)

                if not self.running:
                    break

                self._perform_sync(full=False)

            except KeyboardInterrupt:
                logger.info("Received interrupt signal, stopping...")
                self.running = False
            except Exception as e:
                logger.error(f"Sync service error: {e}", exc_info=True)
                self.stats['syncs_failed'] += 1

        logger.info("Graph Sync Service stopped")
        self._log_final_stats()

    def _perform_sync(self, full: bool = False):
        """
        Perform a sync operation.

        Args:
            full: Whether to perform full sync (True) or incremental (False)
        """
        sync_type = "full" if full else "incremental"
        start_time = time.time()

        try:
            logger.info(f"Starting {sync_type} sync...")

            if full:
                result = self.sync.full_sync()
            else:
                # For incremental sync, we'll just do a full sync for now
                # In production, you might track last sync time and only sync new records
                result = self.sync.full_sync()

            duration = time.time() - start_time

            # Update stats
            self.stats['syncs_completed'] += 1
            self.stats['last_sync_time'] = datetime.now().isoformat()
            self.stats['last_sync_duration'] = duration

            # Check if sync was successful
            if result.get('success'):
                logger.info(
                    f"{sync_type.capitalize()} sync completed in {duration:.2f}s: "
                    f"{result.get('heuristics_synced', 0)} heuristics, "
                    f"{result.get('learnings_synced', 0)} learnings"
                )
            else:
                logger.warning(f"{sync_type.capitalize()} sync completed with warnings: {result.get('message', 'Unknown')}")

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"{sync_type.capitalize()} sync failed after {duration:.2f}s: {e}", exc_info=True)
            self.stats['syncs_failed'] += 1

    def _log_final_stats(self):
        """Log final statistics before shutdown."""
        logger.info("=== Graph Sync Service Statistics ===")
        logger.info(f"Total syncs completed: {self.stats['syncs_completed']}")
        logger.info(f"Total syncs failed: {self.stats['syncs_failed']}")
        if self.stats['last_sync_time']:
            logger.info(f"Last sync: {self.stats['last_sync_time']}")
            logger.info(f"Last sync duration: {self.stats['last_sync_duration']:.2f}s")

    def stop(self):
        """Stop the sync service."""
        self.running = False

    def get_status(self) -> dict:
        """
        Get the current status of the sync service.

        Returns:
            Dictionary with status information
        """
        return {
            'running': self.running,
            'sync_interval': self.sync_interval,
            'stats': self.stats.copy(),
            'graph_available': self.sync.graph.is_available if hasattr(self.sync, 'graph') else False
        }


if __name__ == "__main__":
    # Parse command line arguments
    import argparse

    parser = argparse.ArgumentParser(description='Graph Sync Background Service')
    parser.add_argument(
        '--interval',
        type=int,
        default=300,
        help='Sync interval in seconds (default: 300 = 5 minutes)'
    )
    parser.add_argument(
        '--no-initial-sync',
        action='store_true',
        help='Skip initial full sync on startup'
    )

    args = parser.parse_args()

    # Start service
    service = GraphSyncService(
        sync_interval=args.interval,
        full_sync_on_startup=not args.no_initial_sync
    )

    try:
        service.run()
    except Exception as e:
        logger.error(f"Fatal error in sync service: {e}", exc_info=True)
        sys.exit(1)
