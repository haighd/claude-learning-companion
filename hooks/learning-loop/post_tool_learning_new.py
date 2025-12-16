#!/usr/bin/env python3
"""
Backward-compatible wrapper for post_tool_learning.

Imports from the new consolidated CLC hooks module.
This file maintains compatibility while the migration is in progress.
"""

import sys
from pathlib import Path

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import from consolidated module
from hooks.clc.core.post_hook import (
    AdvisoryVerifier,
    determine_outcome,
    validate_heuristics,
    check_golden_rule_promotion,
    auto_record_failure,
    log_advisory_warning,
    extract_and_record_learnings,
    main,
)

if __name__ == "__main__":
    main()
