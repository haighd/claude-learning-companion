"""CLC Core Hooks - Pre and post tool processing."""

from .pre_hook import (
    ComplexityScorer,
    extract_domain_from_context,
    get_relevant_heuristics,
    get_recent_failures,
    format_learning_context,
)

from .post_hook import (
    AdvisoryVerifier,
    determine_outcome,
    validate_heuristics,
    check_golden_rule_promotion,
    auto_record_failure,
)
