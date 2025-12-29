#!/usr/bin/env python3
"""Check worktree status and print report"""
import subprocess
import os

def run_git(repo_path, *args):
    """Run git command and return output"""
    cmd = ['git', '-C', repo_path] + list(args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout.strip() if result.returncode == 0 else f"ERROR: {result.stderr.strip()}"
    except Exception as e:
        return f"EXCEPTION: {e}"

def main():
    base = "/Users/danhaight/.claude/clc"
    worktrees_base = "/Users/danhaight/.claude/clc-worktrees"

    worktrees = [
        ("sprint-2025-12-29-infra-commands", "group/infra-commands"),
        ("sprint-2025-12-29-hooks-query", "group/hooks-query"),
        ("sprint-2025-12-29-skills-agents", "group/skills-agents"),
    ]

    print("=" * 70)
    print("WORKTREE STATUS REPORT")
    print("=" * 70)

    for wt_name, branch in worktrees:
        wt_path = f"{worktrees_base}/{wt_name}"
        print(f"\n{'=' * 70}")
        print(f"WORKTREE: {wt_name}")
        print(f"PATH: {wt_path}")
        print(f"BRANCH: {branch}")
        print("-" * 70)

        if os.path.exists(wt_path):
            print("EXISTS: Yes")

            # Get git log
            print("\nLATEST 5 COMMITS:")
            log_output = run_git(wt_path, 'log', '--oneline', '-5')
            print(log_output)

            # Get git status
            print("\nUNCOMMITTED CHANGES (git status --short):")
            status_output = run_git(wt_path, 'status', '--short')
            if status_output:
                print(status_output)
            else:
                print("(clean - no uncommitted changes)")
        else:
            print("EXISTS: No - worktree directory not found")

            # Try to get info from main repo
            print("\nChecking branch from main repo...")
            log_output = run_git(base, 'log', '--oneline', '-5', branch)
            if not log_output.startswith("ERROR"):
                print(f"Branch {branch} exists in main repo:")
                print(log_output)
            else:
                print(f"Branch {branch} not found: {log_output}")

    print("\n" + "=" * 70)
    print("END OF REPORT")
    print("=" * 70)

if __name__ == "__main__":
    main()
