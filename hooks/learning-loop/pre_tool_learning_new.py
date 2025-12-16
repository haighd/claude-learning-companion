#!/usr/bin/env python3
"""
Backward-compatible wrapper for pre_tool_learning.

Imports from the new consolidated CLC hooks module.
This file maintains compatibility while the migration is in progress.
"""

import sys
from pathlib import Path

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import from consolidated module
from hooks.clc.core.pre_hook import (
    ComplexityScorer,
    extract_domain_from_context,
    get_relevant_heuristics,
    get_recent_failures,
    format_learning_context,
    record_heuristics_consulted,
    main,
)

if __name__ == "__main__":
    main()
