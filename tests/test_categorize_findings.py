"""Tests for scripts/categorize-findings.py severity categorization."""

import pytest
import sys
import os

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

# Import the module under test
import importlib.util
_spec = importlib.util.spec_from_file_location(
    'categorize_findings',
    os.path.join(os.path.dirname(__file__), '..', 'scripts', 'categorize-findings.py')
)
categorize_findings = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(categorize_findings)


class TestCategorizeComment:
    """Tests for the categorize_comment function."""

    # Critical severity patterns
    @pytest.mark.parametrize('comment', [
        '![critical] This is a security vulnerability',
        '![security-critical] SQL injection detected',
        '**critical** Must fix before merge',
        '![CRITICAL] uppercase should match',
        'Some text ![critical] in the middle',
    ])
    def test_critical_severity(self, comment):
        assert categorize_findings.categorize_comment(comment) == 'critical'

    # High severity patterns
    @pytest.mark.parametrize('comment', [
        '![high] Important issue found',
        '![security-high] XSS vulnerability',
        '**high** Priority fix needed',
        '![HIGH] uppercase should match',
    ])
    def test_high_severity(self, comment):
        assert categorize_findings.categorize_comment(comment) == 'high'

    # Medium severity patterns
    @pytest.mark.parametrize('comment', [
        '![medium] Consider refactoring this',
        '**medium** Code style issue',
        '![MEDIUM] uppercase should match',
    ])
    def test_medium_severity(self, comment):
        assert categorize_findings.categorize_comment(comment) == 'medium'

    # Low severity patterns
    @pytest.mark.parametrize('comment', [
        '![low] Minor suggestion',
        '**low** Optional improvement',
        'nit: add a space here',
        'nitpick: variable naming',
        'minor: typo in comment',
        'NIT: uppercase nit',
        'NITPICK: uppercase nitpick',
    ])
    def test_low_severity(self, comment):
        assert categorize_findings.categorize_comment(comment) == 'low'

    # Default to low for unmatched patterns
    @pytest.mark.parametrize('comment', [
        'This is a general comment without severity',
        'Consider using a different approach',
        'Good job on this implementation!',
        '',  # Empty comment
        'The word critical appears but not as a badge',
    ])
    def test_default_to_low(self, comment):
        """Comments without severity badges should default to low."""
        assert categorize_findings.categorize_comment(comment) == 'low'

    def test_first_match_wins(self):
        """When multiple patterns match, the first (highest) severity wins."""
        # Critical comes before high in pattern order
        comment = '![critical] and also ![high] issue'
        assert categorize_findings.categorize_comment(comment) == 'critical'

    def test_case_insensitive_matching(self):
        """Patterns should match regardless of case."""
        assert categorize_findings.categorize_comment('![CRITICAL]') == 'critical'
        assert categorize_findings.categorize_comment('![Critical]') == 'critical'
        assert categorize_findings.categorize_comment('![cRiTiCaL]') == 'critical'
        assert categorize_findings.categorize_comment('NIT:') == 'low'
        assert categorize_findings.categorize_comment('Nit:') == 'low'


class TestSeverityPatterns:
    """Tests for severity pattern definitions."""

    def test_all_severity_levels_defined(self):
        """Ensure all expected severity levels are defined."""
        expected = {'critical', 'high', 'medium', 'low'}
        assert set(categorize_findings.SEVERITY_PATTERNS.keys()) == expected

    def test_critical_has_patterns(self):
        """Critical should have security-related patterns."""
        patterns = categorize_findings.SEVERITY_PATTERNS['critical']
        assert len(patterns) >= 2
        # Should include security-critical pattern
        assert any('security' in p for p in patterns)

    def test_low_has_nit_patterns(self):
        """Low severity should include nit/nitpick/minor patterns."""
        patterns = categorize_findings.SEVERITY_PATTERNS['low']
        pattern_str = ' '.join(patterns)
        assert 'nit' in pattern_str.lower()


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_string(self):
        """Empty string should return low (default)."""
        assert categorize_findings.categorize_comment('') == 'low'

    def test_whitespace_only(self):
        """Whitespace-only should return low (default)."""
        assert categorize_findings.categorize_comment('   \n\t  ') == 'low'

    def test_unicode_content(self):
        """Unicode content should not break categorization."""
        assert categorize_findings.categorize_comment('![critical] 日本語テスト') == 'critical'
        assert categorize_findings.categorize_comment('emoji 🔥 without badge') == 'low'

    def test_very_long_comment(self):
        """Very long comments should still be categorized."""
        long_comment = '![high] ' + 'x' * 10000
        assert categorize_findings.categorize_comment(long_comment) == 'high'

    def test_badge_in_code_block(self):
        """Badges in code blocks should still match (current behavior)."""
        # Note: This tests current behavior - badges in code blocks DO match
        comment = '```\n![critical] in code\n```'
        assert categorize_findings.categorize_comment(comment) == 'critical'

    def test_multiline_comment(self):
        """Multiline comments should be searchable."""
        comment = """This is line 1.

![high] This is on line 3.

More text here."""
        assert categorize_findings.categorize_comment(comment) == 'high'
