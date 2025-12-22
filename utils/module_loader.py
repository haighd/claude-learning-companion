#!/usr/bin/env python3
"""
Dynamic Module Loader Utility

Provides a centralized way to dynamically load Python modules from file paths
using importlib. This avoids sys.path manipulation and provides consistent
error handling across the codebase.
"""

import importlib.util
from pathlib import Path
from typing import Any, Optional, Tuple


def load_module_from_path(
    module_name: str,
    path: Path
) -> Tuple[Optional[Any], bool]:
    """
    Dynamically load a Python module from a file path.

    Args:
        module_name: Name to assign to the loaded module
        path: Path to the Python file to load

    Returns:
        Tuple of (module, success_flag):
        - If successful: (loaded_module, True)
        - If failed: (None, False)

    Example:
        module, ok = load_module_from_path("context_monitor", Path("watcher/context_monitor.py"))
        if ok:
            status = module.get_context_status()
    """
    if not path.exists():
        return None, False

    spec = importlib.util.spec_from_file_location(module_name, path)
    if not spec or not spec.loader:
        return None, False

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        return module, True
    except (AttributeError, ImportError, ModuleNotFoundError):
        return None, False


def get_module_attribute(
    module_name: str,
    path: Path,
    attribute: str
) -> Tuple[Optional[Any], bool]:
    """
    Load a module and return a specific attribute from it.

    Args:
        module_name: Name to assign to the loaded module
        path: Path to the Python file to load
        attribute: Name of the attribute to retrieve from the module

    Returns:
        Tuple of (attribute_value, success_flag):
        - If successful: (attribute_value, True)
        - If failed: (None, False)

    Example:
        get_context_status, ok = get_module_attribute(
            "context_monitor",
            Path("watcher/context_monitor.py"),
            "get_context_status"
        )
        if ok:
            status = get_context_status()
    """
    module, ok = load_module_from_path(module_name, path)
    if not ok or module is None:
        return None, False

    try:
        attr = getattr(module, attribute)
        return attr, True
    except AttributeError:
        return None, False
