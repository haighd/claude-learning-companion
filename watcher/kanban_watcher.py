"""
CEO Inbox Watcher for Kanban Task Auto-Creation.

Monitors the ceo-inbox/ directory for new decision request files
and automatically creates corresponding Kanban tasks.
"""

import logging
import re
import sys
import time
from pathlib import Path
from typing import Set

# Add CLC to path
CLC_PATH = Path.home() / ".claude" / "clc"
if str(CLC_PATH) not in sys.path:
    sys.path.insert(0, str(CLC_PATH))

from memory.kanban_automation import create_task_from_ceo_inbox

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CEOInboxWatcher:
    """
    Watches the ceo-inbox directory for new markdown files and creates
    Kanban tasks automatically.
    """

    def __init__(self, check_interval: int = 60):
        """
        Initialize the watcher.

        Args:
            check_interval: Seconds between checks (default: 60)
        """
        self.check_interval = check_interval
        self.ceo_inbox_path = CLC_PATH / "ceo-inbox"
        self.processed_files: Set[str] = set()
        self.running = False

    def extract_title_and_priority(self, filepath: Path) -> tuple[str, int]:
        """
        Extract title and priority from a CEO inbox markdown file.

        Looks for YAML frontmatter or first heading.

        Args:
            filepath: Path to the markdown file

        Returns:
            Tuple of (title, priority)
        """
        try:
            content = filepath.read_text()

            # Try to extract from YAML frontmatter
            frontmatter_match = re.search(
                r'^---\s*\n(.*?)\n---',
                content,
                re.MULTILINE | re.DOTALL
            )

            title = filepath.stem.replace('-', ' ').title()
            priority = 2  # Default: high priority

            if frontmatter_match:
                frontmatter = frontmatter_match.group(1)

                # Extract title
                title_match = re.search(r'title:\s*(.+)', frontmatter, re.IGNORECASE)
                if title_match:
                    title = title_match.group(1).strip().strip('"\'')

                # Extract priority
                priority_match = re.search(r'priority:\s*(\d+)', frontmatter, re.IGNORECASE)
                if priority_match:
                    priority = int(priority_match.group(1))
                elif re.search(r'urgency:\s*(high|critical)', frontmatter, re.IGNORECASE):
                    priority = 3
                elif re.search(r'urgency:\s*low', frontmatter, re.IGNORECASE):
                    priority = 1

            else:
                # Fallback: use first heading
                heading_match = re.search(r'^#\s+(.+)', content, re.MULTILINE)
                if heading_match:
                    title = heading_match.group(1).strip()

            return title, priority

        except Exception as e:
            logger.warning(f"Failed to parse {filepath.name}: {e}")
            return filepath.stem.replace('-', ' ').title(), 2

    def scan_inbox(self):
        """
        Scan the CEO inbox directory for new files and create tasks.
        """
        try:
            # Ensure directory exists
            if not self.ceo_inbox_path.exists():
                logger.debug(f"CEO inbox directory does not exist yet: {self.ceo_inbox_path}")
                return

            # Find all markdown files
            md_files = list(self.ceo_inbox_path.glob("*.md"))

            # Filter to only new files
            new_files = [
                f for f in md_files
                if str(f.relative_to(CLC_PATH)) not in self.processed_files
                and f.name not in ('.gitkeep', 'TEMPLATE.md', 'README.md')
            ]

            if new_files:
                logger.info(f"Found {len(new_files)} new CEO inbox file(s)")

            for filepath in new_files:
                try:
                    rel_path = str(filepath.relative_to(CLC_PATH))
                    title, priority = self.extract_title_and_priority(filepath)

                    # Create Kanban task
                    task_id = create_task_from_ceo_inbox(
                        filepath=rel_path,
                        title=f"CEO Decision: {title}",
                        priority=priority
                    )

                    if task_id:
                        logger.info(f"Created task {task_id} from {filepath.name}")
                        self.processed_files.add(rel_path)
                    else:
                        logger.warning(f"Failed to create task from {filepath.name}")

                except Exception as e:
                    logger.error(f"Error processing {filepath.name}: {e}")

        except Exception as e:
            logger.error(f"Error scanning CEO inbox: {e}")

    def run(self):
        """
        Start the watcher loop.
        """
        self.running = True
        logger.info(f"CEO Inbox Watcher started: checking every {self.check_interval}s")

        # Initial scan to catch existing files
        self.scan_inbox()

        while self.running:
            try:
                time.sleep(self.check_interval)
                self.scan_inbox()
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, stopping...")
                self.running = False
            except Exception as e:
                logger.error(f"Watcher error: {e}")

        logger.info("CEO Inbox Watcher stopped")

    def stop(self):
        """Stop the watcher."""
        self.running = False


if __name__ == "__main__":
    # Ensure ceo-inbox directory exists
    ceo_inbox = CLC_PATH / "ceo-inbox"
    ceo_inbox.mkdir(exist_ok=True)

    # Create .gitkeep if it doesn't exist
    gitkeep = ceo_inbox / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()

    # Start watcher
    watcher = CEOInboxWatcher(check_interval=60)
    watcher.run()
