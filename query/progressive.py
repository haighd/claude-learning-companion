#!/usr/bin/env python3
"""
Progressive Disclosure Query System for CLC.

Context-aware loading with tiered retrieval, confidence scoring, and token budget management.

Tiers:
- Essential: Golden rules and critical invariants (~500 tokens)
- Recommended: Domain-relevant heuristics and recent learnings (~2-5k tokens)
- Full: Complete context including experiments, ADRs, spike reports (~5-10k tokens)

Relevance scoring (0.0-1.0) based on:
- Domain match (30%)
- Keyword overlap (25%)
- Recency (20%)
- Confidence/validation history (25%)

GitHub Issue: #65
Implementation Date: December 29, 2025
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


class LoadingTier(Enum):
    """Loading tiers for progressive disclosure."""
    ESSENTIAL = "essential"      # ~500 tokens - critical rules only
    RECOMMENDED = "recommended"  # ~2-5k tokens - domain-relevant content
    FULL = "full"               # ~5-10k tokens - complete context


@dataclass
class ScoredItem:
    """A knowledge item with relevance scoring."""
    item: Dict[str, Any]
    relevance_score: float  # 0.0 to 1.0
    token_estimate: int
    source_tier: LoadingTier
    match_reasons: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.relevance_score = max(0.0, min(1.0, self.relevance_score))


@dataclass
class TokenBudget:
    """Token budget manager for progressive loading."""
    total_budget: int
    essential_reserved: int = 500
    recommended_reserved: int = 2500
    used: int = 0

    @property
    def remaining(self) -> int:
        return max(0, self.total_budget - self.used)

    def consume(self, tokens: int) -> bool:
        if self.used + tokens > self.total_budget:
            return False
        self.used += tokens
        return True

    def can_fit(self, tokens: int) -> bool:
        return self.used + tokens <= self.total_budget


class RelevanceScorer:
    """Calculates relevance scores for knowledge items."""

    DOMAIN_MATCH_WEIGHT = 0.30
    KEYWORD_WEIGHT = 0.25
    RECENCY_WEIGHT = 0.20
    CONFIDENCE_WEIGHT = 0.15
    VALIDATION_WEIGHT = 0.10

    # Recency thresholds (in hours) for scoring
    HOURS_VERY_RECENT = 1       # Last hour - highest recency score
    HOURS_IN_DAY = 24           # Within 24 hours
    HOURS_IN_WEEK = 168         # 7 * 24 = 168 hours
    HOURS_IN_MONTH = 720        # ~30 * 24 = 720 hours

    STOPWORDS = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'to', 'of',
        'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through',
        'and', 'but', 'if', 'or', 'because', 'until', 'while', 'this', 'that'
    }

    def __init__(self, task_description: str, domain: Optional[str] = None):
        self.task_description = task_description.lower()
        self.domain = domain.lower() if domain else None
        self.task_keywords = self._extract_keywords(task_description)

    def _extract_keywords(self, text: str) -> set:
        words = re.findall(r'\b[a-z][a-z0-9_-]{2,}\b', text.lower())
        return {w for w in words if w not in self.STOPWORDS}

    def score_heuristic(self, heuristic: Dict[str, Any]) -> float:
        score = 0.0
        h_domain = (heuristic.get('domain') or '').lower()

        # Domain match
        if self.domain and h_domain == self.domain:
            score += self.DOMAIN_MATCH_WEIGHT
        elif self.domain and self.domain in h_domain:
            score += self.DOMAIN_MATCH_WEIGHT * 0.5

        # Keyword overlap
        rule_text = f"{heuristic.get('rule', '')} {heuristic.get('explanation', '')}".lower()
        rule_keywords = self._extract_keywords(rule_text)
        if rule_keywords and self.task_keywords:
            overlap = len(rule_keywords & self.task_keywords)
            max_overlap = min(len(rule_keywords), len(self.task_keywords))
            if max_overlap > 0:
                score += self.KEYWORD_WEIGHT * (overlap / max_overlap)

        # Recency
        if heuristic.get('created_at'):
            score += self._recency_score(heuristic['created_at']) * self.RECENCY_WEIGHT

        # Confidence
        confidence = heuristic.get('confidence', 0.5)
        score += confidence * self.CONFIDENCE_WEIGHT

        # Validation history
        validated = heuristic.get('times_validated', 0)
        violated = heuristic.get('times_violated', 0)
        total = validated + violated
        if total > 0:
            score += (validated / total) * self.VALIDATION_WEIGHT

        return min(1.0, score)

    def score_learning(self, learning: Dict[str, Any]) -> float:
        score = 0.0
        l_domain = (learning.get('domain') or '').lower()

        if self.domain and l_domain == self.domain:
            score += self.DOMAIN_MATCH_WEIGHT

        text = f"{learning.get('title', '')} {learning.get('summary', '')}".lower()
        keywords = self._extract_keywords(text)
        if keywords and self.task_keywords:
            overlap = len(keywords & self.task_keywords)
            if overlap > 0:
                score += self.KEYWORD_WEIGHT * (overlap / min(len(keywords), len(self.task_keywords)))

        if learning.get('created_at'):
            score += self._recency_score(learning['created_at']) * self.RECENCY_WEIGHT * 1.5

        if learning.get('type', '').lower() == 'failure':
            score += 0.1

        return min(1.0, score)

    def _recency_score(self, timestamp: Any) -> float:
        if timestamp is None:
            return 0.5
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                return 0.5
        if not isinstance(timestamp, datetime):
            return 0.5

        now = datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        age_hours = (now - timestamp).total_seconds() / 3600
        if age_hours < self.HOURS_VERY_RECENT:
            return 1.0
        elif age_hours < self.HOURS_IN_DAY:
            return 0.8
        elif age_hours < self.HOURS_IN_WEEK:
            return 0.5
        elif age_hours < self.HOURS_IN_MONTH:
            return 0.2
        return 0.1


class ProgressiveLoader:
    """Progressive disclosure loader for CLC knowledge."""

    CHARS_PER_TOKEN = 4

    def __init__(
        self,
        task_description: str,
        domain: Optional[str] = None,
        max_tokens: int = 5000,
        tier: LoadingTier = LoadingTier.RECOMMENDED
    ):
        self.task_description = task_description
        self.domain = domain
        self.tier = tier
        self.budget = TokenBudget(total_budget=max_tokens)
        self.scorer = RelevanceScorer(task_description, domain)
        self.loaded_items: List[ScoredItem] = []

    def estimate_tokens(self, text: str) -> int:
        return len(text) // self.CHARS_PER_TOKEN + 1

    def load_essential(self, golden_rules: str, critical_invariants: List[Dict] = None) -> List[ScoredItem]:
        items = []
        gr_tokens = self.estimate_tokens(golden_rules)
        if self.budget.consume(gr_tokens):
            items.append(ScoredItem(
                item={'type': 'golden_rules', 'content': golden_rules},
                relevance_score=1.0,
                token_estimate=gr_tokens,
                source_tier=LoadingTier.ESSENTIAL,
                match_reasons=['Foundational rules - always included']
            ))
        self.loaded_items.extend(items)
        return items

    def load_recommended(self, heuristics: List[Dict], learnings: List[Dict], min_relevance: float = 0.3) -> List[ScoredItem]:
        if self.tier == LoadingTier.ESSENTIAL:
            return []

        candidates = []
        for h in heuristics:
            score = self.scorer.score_heuristic(h)
            if score >= min_relevance:
                text = f"{h.get('rule', '')} {h.get('explanation', '')}"
                candidates.append(ScoredItem(
                    item={'type': 'heuristic', **h},
                    relevance_score=score,
                    token_estimate=self.estimate_tokens(text),
                    source_tier=LoadingTier.RECOMMENDED,
                    match_reasons=[f"Domain: {h.get('domain', 'general')}"]
                ))

        for l in learnings:
            score = self.scorer.score_learning(l)
            if score >= min_relevance:
                text = f"{l.get('title', '')} {l.get('summary', '')}"
                candidates.append(ScoredItem(
                    item={'type': 'learning', **l},
                    relevance_score=score,
                    token_estimate=self.estimate_tokens(text),
                    source_tier=LoadingTier.RECOMMENDED,
                    match_reasons=[f"Type: {l.get('type', 'observation')}"]
                ))

        candidates.sort(key=lambda x: x.relevance_score, reverse=True)
        items = []
        for c in candidates:
            if self.budget.can_fit(c.token_estimate):
                self.budget.consume(c.token_estimate)
                items.append(c)
        self.loaded_items.extend(items)
        return items

    def get_summary(self) -> Dict[str, Any]:
        by_type = {}
        for item in self.loaded_items:
            t = item.item.get('type', 'unknown')
            if t not in by_type:
                by_type[t] = {'count': 0, 'tokens': 0}
            by_type[t]['count'] += 1
            by_type[t]['tokens'] += item.token_estimate

        return {
            'tier': self.tier.value,
            'domain': self.domain,
            'total_items': len(self.loaded_items),
            'tokens_used': self.budget.used,
            'tokens_remaining': self.budget.remaining,
            'by_type': by_type
        }

    def format_context(self) -> str:
        lines = [
            f"# Progressive Context (tier={self.tier.value})",
            f"# Task: {self.task_description[:80]}...",
            f"# Budget: {self.budget.used}/{self.budget.total_budget} tokens",
            ""
        ]
        if self.domain:
            lines.insert(2, f"# Domain: {self.domain}")

        by_tier = {t: [] for t in LoadingTier}
        for item in self.loaded_items:
            by_tier[item.source_tier].append(item)

        for tier in LoadingTier:
            items = by_tier[tier]
            if not items:
                continue
            lines.append(f"## {tier.value.upper()} ({len(items)} items)")
            lines.append("")
            for item in sorted(items, key=lambda x: x.relevance_score, reverse=True):
                t = item.item.get('type', 'unknown')
                if t == 'golden_rules':
                    lines.append(item.item.get('content', ''))
                elif t == 'heuristic':
                    lines.append(f"- **{item.item.get('rule', 'Unknown')}** (rel={item.relevance_score:.2f})")
                elif t == 'learning':
                    lines.append(f"- **{item.item.get('title', 'Unknown')}** ({item.item.get('type', 'obs')})")
                lines.append("")
        return "\n".join(lines)


def progressive_query(
    task_description: str,
    domain: Optional[str] = None,
    tier: str = "recommended",
    max_tokens: int = 5000,
    golden_rules: str = "",
    heuristics: List[Dict] = None,
    learnings: List[Dict] = None
) -> Dict[str, Any]:
    """Main entry point for progressive disclosure queries."""
    tier_map = {
        "essential": LoadingTier.ESSENTIAL,
        "recommended": LoadingTier.RECOMMENDED,
        "full": LoadingTier.FULL
    }
    loading_tier = tier_map.get(tier.lower(), LoadingTier.RECOMMENDED)

    loader = ProgressiveLoader(
        task_description=task_description,
        domain=domain,
        max_tokens=max_tokens,
        tier=loading_tier
    )

    loader.load_essential(golden_rules)
    if loading_tier in (LoadingTier.RECOMMENDED, LoadingTier.FULL):
        loader.load_recommended(heuristics or [], learnings or [])

    return {
        'context': loader.format_context(),
        'summary': loader.get_summary(),
        'metadata': {
            'task': task_description[:100],
            'domain': domain,
            'tier': tier,
            'tokens_used': loader.budget.used,
            'items_loaded': len(loader.loaded_items)
        }
    }


if __name__ == "__main__":
    result = progressive_query(
        task_description="Implement secure user authentication",
        domain="security",
        tier="recommended",
        max_tokens=2000,
        golden_rules="# Golden Rules\n1. Query CLC before acting\n2. Document failures",
        heuristics=[{'rule': 'Validate input', 'domain': 'security', 'confidence': 0.9}],
        learnings=[{'title': 'SQL injection fix', 'type': 'failure', 'domain': 'security'}]
    )
    print(json.dumps(result['summary'], indent=2))
