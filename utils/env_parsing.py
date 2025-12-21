#!/usr/bin/env python3
"""
Shared utilities for safe environment variable parsing.

Provides type-safe parsing of environment variables with fallback defaults
and helpful error messages. Used across the CLC codebase to ensure consistent
configuration handling.

Usage:
    from utils.env_parsing import safe_env_int, safe_env_float

    CONTEXT_BUDGET = safe_env_int('CONTEXT_WINDOW_SIZE', '200000')
    THRESHOLD = safe_env_float('CONTEXT_CHECKPOINT_THRESHOLD', '0.6')
"""

import os
import sys
from typing import Callable, TypeVar

T = TypeVar('T', int, float)


def safe_env_parser(
    name: str,
    default: str,
    converter: Callable[[str], T],
    error_value: T,
    module_name: str = "env_parsing"
) -> T:
    """Safely parse environment variable with helpful error message.

    Args:
        name: Environment variable name
        default: Default value as string
        converter: Function to convert string to target type (int or float)
        error_value: Value to return if both env var and default fail to parse
        module_name: Name of calling module for error messages

    Returns:
        Parsed value, or error_value if parsing fails
    """
    value_str = os.environ.get(name)
    if value_str is not None:
        try:
            return converter(value_str)
        except ValueError:
            sys.stderr.write(
                f"[{module_name}] Invalid value for {name}: '{value_str}', "
                f"using default {default}\n"
            )

    try:
        return converter(default)
    except ValueError:
        sys.stderr.write(
            f"[{module_name}] Invalid default for {name}: '{default}', "
            f"using {error_value}\n"
        )
        return error_value


def safe_env_int(
    name: str,
    default: str,
    module_name: str = "env_parsing",
    error_value: int = 0
) -> int:
    """Safely parse int from environment variable.

    Args:
        name: Environment variable name
        default: Default value as string
        module_name: Name of calling module for error messages
        error_value: Value to return on error. Defaults to 0.

    Returns:
        Parsed integer, or error_value if parsing fails
    """
    return safe_env_parser(name, default, int, error_value, module_name)


def safe_env_float(
    name: str,
    default: str,
    module_name: str = "env_parsing",
    error_value: float = 1.1
) -> float:
    """Safely parse float from environment variable.

    Args:
        name: Environment variable name
        default: Default value as string
        module_name: Name of calling module for error messages
        error_value: Value to return on error. Defaults to 1.1 to disable
                     threshold-based features on config errors (prevents
                     checkpoint spam that would occur with 0.0).

    Returns:
        Parsed float, or error_value if parsing fails
    """
    return safe_env_parser(name, default, float, error_value, module_name)
