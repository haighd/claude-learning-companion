#!/usr/bin/env python3
"""
Shared formatting utilities.

Provides consistent formatting functions used across the CLC codebase.

Usage:
    from utils.formatting import format_usage_percentage

    usage_str = format_usage_percentage(0.65, "my_module")  # "65%"
"""

import sys
from typing import Any, Tuple


def format_usage_percentage(
    usage: Any,
    module_name: str = "formatting"
) -> Tuple[str, bool]:
    """Format a usage value as a percentage string.

    Handles invalid values gracefully by returning a descriptive string
    instead of raising an exception.

    Args:
        usage: The usage value (expected to be a float 0.0-1.0)
        module_name: Name of calling module for error messages

    Returns:
        Tuple of (formatted_string, is_valid) where:
        - formatted_string: "65%" for valid values, "(invalid value: ...)" otherwise
        - is_valid: True if the value was valid and formatted correctly
    """
    try:
        usage_pct = float(usage) * 100
        return f"{usage_pct:.0f}%", True
    except (ValueError, TypeError):
        sys.stderr.write(
            f"[{module_name}] Invalid value for estimated_usage: {repr(usage)}, "
            f"showing raw value.\n"
        )
        return f"(invalid value: {repr(usage)})", False
