"""
Claude Learning Companion (CLC) - Hooks Module

Consolidated hook system for the learning loop.

Modules:
- core: Pre and post tool hooks
- security: Advisory verification patterns
- trails: File path tracking and trail laying
"""

from pathlib import Path

# Package info
__version__ = "2.0.0"
__package_path__ = Path(__file__).parent

# Convenience imports (with fallback for direct execution)
try:
    from .core.pre_hook import ComplexityScorer, extract_domain_from_context
    from .core.post_hook import AdvisoryVerifier, determine_outcome
    from .security.patterns import RISKY_PATTERNS
    from .trails.trail_helper import extract_file_paths, lay_trails
except ImportError:
    # Fallback for when modules are run directly
    ComplexityScorer = None
    AdvisoryVerifier = None
    extract_domain_from_context = None
    determine_outcome = None
    RISKY_PATTERNS = None
    extract_file_paths = None
    lay_trails = None
