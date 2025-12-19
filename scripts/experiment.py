#!/usr/bin/env python3
"""
Experiment Manager: Git worktree isolation for risky CLC changes.

Commands:
  start [description]  - Create isolated worktree for experiment
  status               - Show active experiments
  merge [exp_id]       - Integrate successful experiment back to main
  discard [exp_id]     - Remove failed experiment
  list                 - List all experiments

Part of the Auto-Claude Integration (P1: Worktree Isolation).
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import uuid

# Paths
CLC_PATH = Path.home() / ".claude" / "clc"
WORKTREES_PATH = CLC_PATH / ".worktrees"
EXPERIMENTS_FILE = CLC_PATH / ".experiments.json"
DB_PATH = CLC_PATH / "memory" / "index.db"

# Constants
MAX_EXP_ID_LENGTH = 64


def validate_exp_id(exp_id: str) -> bool:
    """Validate experiment ID to prevent command injection.

    Must start with an alphanumeric character and contain only alphanumerics,
    hyphens, and underscores. Leading hyphens are prevented to avoid shell flag
    confusion.
    """
    if not exp_id or len(exp_id) > MAX_EXP_ID_LENGTH:
        return False
    return bool(re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]*', exp_id))


def generate_id() -> str:
    """Generate a safe alphanumeric experiment ID."""
    return uuid.uuid4().hex[:12]


def run_git(*args: str, cwd: Path = None, check: bool = True,
            capture_output: bool = False) -> subprocess.CompletedProcess:
    """Run git command safely using argument list."""
    cmd = ['git'] + list(args)
    return subprocess.run(
        cmd,
        cwd=cwd or CLC_PATH,
        check=check,
        capture_output=capture_output,
        text=True
    )


def get_default_branch() -> str:
    """Detect the default branch name."""
    try:
        result = run_git(
            'symbolic-ref', 'refs/remotes/origin/HEAD',
            capture_output=True, check=False
        )
        if result.returncode == 0:
            return result.stdout.strip().split('/')[-1]
    except Exception:
        pass

    # Try to find main or master
    result = run_git('branch', '-l', 'main', 'master', capture_output=True, check=False)
    branches = result.stdout.strip().split('\n')
    for branch in branches:
        branch = branch.strip().lstrip('* ')
        if branch in ('main', 'master'):
            return branch

    return 'main'


def get_current_branch() -> str:
    """Get the current branch name."""
    result = run_git('rev-parse', '--abbrev-ref', 'HEAD', capture_output=True)
    return result.stdout.strip()


def is_working_tree_clean() -> bool:
    """Check if the git working tree has no uncommitted changes."""
    result = run_git('diff-index', '--quiet', 'HEAD', '--', check=False, capture_output=True)
    return result.returncode == 0


def load_experiments() -> Dict:
    """Load experiments metadata."""
    if EXPERIMENTS_FILE.exists():
        try:
            return json.loads(EXPERIMENTS_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {"experiments": {}, "active": None}


def save_experiments(data: Dict):
    """Save experiments metadata."""
    EXPERIMENTS_FILE.write_text(json.dumps(data, indent=2))


def get_worktree_path(exp_id: str) -> Path:
    """Get worktree path for an experiment."""
    return WORKTREES_PATH / f"exp-{exp_id}"


# === COMMANDS ===

def cmd_start(description: str) -> int:
    """Start a new experiment with isolated worktree."""
    # Check for uncommitted changes
    if not is_working_tree_clean():
        print("Error: Working tree has uncommitted changes.")
        print("Commit or stash your changes before starting an experiment.")
        return 1

    # Generate experiment ID
    exp_id = generate_id()
    if not validate_exp_id(exp_id):
        print(f"Error: Generated invalid experiment ID: {exp_id}")
        return 1

    worktree_path = get_worktree_path(exp_id)
    branch_name = f"exp-{exp_id}"

    print(f"Creating experiment: {exp_id}")
    print(f"Description: {description}")
    print()

    try:
        # Ensure worktrees directory exists
        WORKTREES_PATH.mkdir(parents=True, exist_ok=True)

        # Create worktree with new branch
        print(f"Creating worktree at {worktree_path}...")
        run_git('worktree', 'add', str(worktree_path), '-b', branch_name)

        # Copy database to isolated worktree
        worktree_db_dir = worktree_path / "memory"
        worktree_db_dir.mkdir(parents=True, exist_ok=True)

        if DB_PATH.exists():
            print("Copying database to isolated environment...")
            shutil.copy(DB_PATH, worktree_db_dir / "index.db")

        # Save experiment metadata
        experiments = load_experiments()
        experiments["experiments"][exp_id] = {
            "id": exp_id,
            "description": description,
            "branch": branch_name,
            "worktree": str(worktree_path),
            "created_at": datetime.now().isoformat(),
            "status": "active"
        }
        experiments["active"] = exp_id
        save_experiments(experiments)

        print()
        print(f"Experiment '{exp_id}' created successfully!")
        print()
        print("To work in the experiment:")
        print(f"  cd {worktree_path}")
        print()
        print("When done:")
        print(f"  /experiment merge {exp_id}   # If successful")
        print(f"  /experiment discard {exp_id} # If failed")
        return 0

    except subprocess.CalledProcessError as e:
        print(f"Error creating worktree: {e}")
        # Cleanup on failure
        if worktree_path.exists():
            shutil.rmtree(worktree_path, ignore_errors=True)
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_status() -> int:
    """Show status of all experiments."""
    experiments = load_experiments()

    if not experiments["experiments"]:
        print("No experiments found.")
        print()
        print("Start one with: /experiment start \"description\"")
        return 0

    print("Experiments:")
    print("=" * 70)

    for exp_id, exp in experiments["experiments"].items():
        is_active = experiments.get("active") == exp_id
        status_marker = " [ACTIVE]" if is_active else ""

        print(f"\nID: {exp_id}{status_marker}")
        print(f"  Description: {exp['description']}")
        print(f"  Branch: {exp['branch']}")
        print(f"  Created: {exp['created_at']}")
        print(f"  Status: {exp['status']}")

        # Check if worktree still exists
        worktree_path = Path(exp['worktree'])
        if worktree_path.exists():
            print(f"  Path: {worktree_path}")
        else:
            print(f"  Path: {worktree_path} (MISSING)")

    print()
    return 0


def cmd_list() -> int:
    """List all experiments (alias for status)."""
    return cmd_status()


def cmd_merge(exp_id: str = None) -> int:
    """Merge successful experiment back to main."""
    experiments = load_experiments()

    # Use active experiment if none specified
    if not exp_id:
        exp_id = experiments.get("active")
        if not exp_id:
            print("Error: No active experiment. Specify an experiment ID.")
            print("Usage: /experiment merge <exp_id>")
            return 1

    if not validate_exp_id(exp_id):
        print(f"Error: Invalid experiment ID: {exp_id}")
        return 1

    if exp_id not in experiments["experiments"]:
        print(f"Error: Experiment '{exp_id}' not found.")
        return 1

    exp = experiments["experiments"][exp_id]
    worktree_path = Path(exp["worktree"])
    branch_name = exp["branch"]

    print(f"Merging experiment: {exp_id}")
    print(f"Description: {exp['description']}")
    print()

    # Check for uncommitted changes in main
    if not is_working_tree_clean():
        print("Error: Main worktree has uncommitted changes.")
        print("Commit or stash before merging.")
        return 1

    try:
        # Get default branch
        default_branch = get_default_branch()
        current_branch = get_current_branch()

        # Checkout default branch if not already there
        if current_branch != default_branch:
            print(f"Switching to {default_branch}...")
            run_git('checkout', default_branch)

        # Merge the experiment branch
        print(f"Merging {branch_name}...")
        run_git('merge', '--no-ff', '-m', f'Merge experiment {exp_id}: {exp["description"]}', branch_name)

        # Merge databases if experiment has one
        exp_db = worktree_path / "memory" / "index.db"
        if exp_db.exists() and DB_PATH.exists():
            print("Merging databases...")
            # For now, we just keep the main database
            # A full implementation would merge records
            print("  (Database merge: keeping main, discarding experiment changes)")

        # Cleanup worktree
        print("Cleaning up worktree...")
        run_git('worktree', 'remove', str(worktree_path), check=False)

        # Delete experiment branch
        print(f"Deleting branch {branch_name}...")
        run_git('branch', '-d', branch_name, check=False)

        # Update experiment metadata
        exp["status"] = "merged"
        exp["merged_at"] = datetime.now().isoformat()
        if experiments.get("active") == exp_id:
            experiments["active"] = None
        save_experiments(experiments)

        print()
        print(f"Experiment '{exp_id}' merged successfully!")
        return 0

    except subprocess.CalledProcessError as e:
        print(f"Error during merge: {e}")
        print()
        print("You may need to resolve conflicts manually.")
        print(f"  Experiment branch: {branch_name}")
        print(f"  Worktree: {worktree_path}")
        return 1


def cmd_discard(exp_id: str = None) -> int:
    """Discard a failed experiment."""
    experiments = load_experiments()

    # Use active experiment if none specified
    if not exp_id:
        exp_id = experiments.get("active")
        if not exp_id:
            print("Error: No active experiment. Specify an experiment ID.")
            print("Usage: /experiment discard <exp_id>")
            return 1

    if not validate_exp_id(exp_id):
        print(f"Error: Invalid experiment ID: {exp_id}")
        return 1

    if exp_id not in experiments["experiments"]:
        print(f"Error: Experiment '{exp_id}' not found.")
        return 1

    exp = experiments["experiments"][exp_id]
    worktree_path = Path(exp["worktree"])
    branch_name = exp["branch"]

    print(f"Discarding experiment: {exp_id}")
    print(f"Description: {exp['description']}")
    print()

    errors = []

    # Remove worktree
    if worktree_path.exists():
        print(f"Removing worktree {worktree_path}...")
        try:
            run_git('worktree', 'remove', '--force', str(worktree_path))
        except subprocess.CalledProcessError as e:
            errors.append(f"Worktree removal: {e}")
            # Try manual removal
            try:
                shutil.rmtree(worktree_path)
                run_git('worktree', 'prune')
            except Exception as e2:
                errors.append(f"Manual cleanup: {e2}")

    # Delete branch
    print(f"Deleting branch {branch_name}...")
    try:
        run_git('branch', '-D', branch_name)
    except subprocess.CalledProcessError as e:
        errors.append(f"Branch deletion: {e}")

    # Update experiment metadata
    exp["status"] = "discarded"
    exp["discarded_at"] = datetime.now().isoformat()
    if experiments.get("active") == exp_id:
        experiments["active"] = None
    save_experiments(experiments)

    if errors:
        print()
        print("Warnings during cleanup:")
        for err in errors:
            print(f"  - {err}")

    print()
    print(f"Experiment '{exp_id}' discarded.")
    return 0


def cmd_clean() -> int:
    """Clean up stale worktrees and branches."""
    print("Cleaning up stale experiment artifacts...")

    # Prune worktrees
    run_git('worktree', 'prune')

    # Find orphaned experiment branches
    result = run_git('branch', '--list', 'exp-*', capture_output=True)
    branches = [b.strip().lstrip('* ') for b in result.stdout.strip().split('\n') if b.strip()]

    experiments = load_experiments()
    active_branches = {exp["branch"] for exp in experiments["experiments"].values()
                       if exp["status"] == "active"}

    orphaned = [b for b in branches if b not in active_branches]

    if orphaned:
        print(f"Found {len(orphaned)} orphaned branches:")
        for branch in orphaned:
            print(f"  - {branch}")
        print()
        response = input("Delete orphaned branches? [y/N]: ")
        if response.lower() == 'y':
            for branch in orphaned:
                try:
                    run_git('branch', '-D', branch)
                    print(f"  Deleted {branch}")
                except subprocess.CalledProcessError:
                    print(f"  Failed to delete {branch}")

    # Clean up worktrees directory
    if WORKTREES_PATH.exists():
        for item in WORKTREES_PATH.iterdir():
            if item.is_dir() and item.name.startswith('exp-'):
                exp_id = item.name[4:]  # Remove 'exp-' prefix
                if exp_id not in experiments["experiments"] or \
                   experiments["experiments"][exp_id]["status"] != "active":
                    print(f"Removing orphaned worktree: {item}")
                    shutil.rmtree(item, ignore_errors=True)

    print("Cleanup complete.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Manage isolated experiments using git worktrees",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  start <description>  Create new experiment
  status               Show all experiments
  list                 Alias for status
  merge [exp_id]       Merge successful experiment
  discard [exp_id]     Discard failed experiment
  clean                Clean up stale artifacts

Examples:
  %(prog)s start "test new heuristic logic"
  %(prog)s status
  %(prog)s merge abc123def456
  %(prog)s discard
        """
    )

    parser.add_argument('command', choices=['start', 'status', 'list', 'merge', 'discard', 'clean'],
                        help='Command to run')
    parser.add_argument('args', nargs='*', help='Command arguments')

    args = parser.parse_args()

    # Ensure we're in the CLC directory
    os.chdir(CLC_PATH)

    if args.command == 'start':
        if not args.args:
            print("Error: Description required for start command")
            print("Usage: experiment start \"description\"")
            return 1
        description = ' '.join(args.args)
        return cmd_start(description)

    elif args.command == 'status':
        return cmd_status()

    elif args.command == 'list':
        return cmd_list()

    elif args.command == 'merge':
        exp_id = args.args[0] if args.args else None
        return cmd_merge(exp_id)

    elif args.command == 'discard':
        exp_id = args.args[0] if args.args else None
        return cmd_discard(exp_id)

    elif args.command == 'clean':
        return cmd_clean()

    return 0


if __name__ == "__main__":
    sys.exit(main())
