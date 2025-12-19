#!/usr/bin/env python3
"""
Relationship Detector: Auto-detect semantic relationships between heuristics.

Uses text similarity and keyword analysis to find:
- Similar heuristics (SIMILAR_TO)
- Complementary heuristics (COMPLEMENTS)
- Conflicting heuristics (CONFLICTS_WITH)

Part of the Auto-Claude Integration (P3: Graph-Based Memory).
"""

import logging
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

from graph_store import get_graph_store

logger = logging.getLogger(__name__)

# Paths
CLC_PATH = Path.home() / ".claude" / "clc"
DB_PATH = CLC_PATH / "memory" / "index.db"

# Relationship thresholds
SIMILARITY_THRESHOLD = 0.4
COMPLEMENT_THRESHOLD = 0.3
CONFLICT_THRESHOLD = 0.5

# Conflict indicator words
CONFLICT_INDICATORS = {
    # Opposing patterns
    ('always', 'never'),
    ('must', 'should not'),
    ('do', 'avoid'),
    ('use', 'dont use'),
    ('enable', 'disable'),
    ('sync', 'async'),
    ('blocking', 'non-blocking'),
    ('mutable', 'immutable'),
    ('global', 'local'),
    ('eager', 'lazy'),
}

# Complement indicator words
COMPLEMENT_INDICATORS = {
    # Related concepts
    'also', 'additionally', 'furthermore', 'moreover',
    'combined with', 'along with', 'together with',
    'related', 'similar', 'likewise',
}


@dataclass
class RelationshipCandidate:
    """A candidate relationship between two heuristics."""
    heuristic_id_1: int
    heuristic_id_2: int
    relationship_type: str  # SIMILAR_TO, COMPLEMENTS, CONFLICTS_WITH
    score: float
    reason: str


class RelationshipDetector:
    """
    Detects semantic relationships between heuristics.

    Uses multiple signals:
    - Jaccard similarity of keywords
    - Domain overlap
    - Conflict indicator detection
    - Complement indicator detection
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.graph = get_graph_store()

    def get_db_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def extract_keywords(self, text: str) -> Set[str]:
        """Extract keywords from text."""
        if not text:
            return set()

        # Lowercase and extract words
        text = text.lower()
        words = re.findall(r'\b[a-z]{3,}\b', text)

        # Filter stopwords
        stopwords = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all',
            'can', 'her', 'was', 'one', 'our', 'out', 'has', 'have',
            'been', 'were', 'being', 'their', 'there', 'this', 'that',
            'with', 'from', 'will', 'when', 'what', 'which', 'should',
            'would', 'could', 'about', 'into', 'more', 'some', 'such',
            'than', 'then', 'these', 'those', 'only', 'over', 'just',
        }

        return {w for w in words if w not in stopwords}

    def jaccard_similarity(self, set1: Set[str], set2: Set[str]) -> float:
        """Calculate Jaccard similarity between two sets."""
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    def detect_conflict(self, text1: str, text2: str) -> Tuple[bool, str]:
        """
        Detect if two heuristics might conflict.

        Returns:
            (is_conflict, reason)
        """
        text1_lower = text1.lower()
        text2_lower = text2.lower()

        for word1, word2 in CONFLICT_INDICATORS:
            # Check if one text has word1 and other has word2
            if ((word1 in text1_lower and word2 in text2_lower) or
                (word2 in text1_lower and word1 in text2_lower)):
                return True, f"Opposing terms: '{word1}' vs '{word2}'"

        # Check for negation patterns
        if ('not ' in text1_lower or 'dont ' in text1_lower or "don't" in text1_lower):
            # Extract the verb/action being negated
            negated = re.findall(r"(?:not|don'?t)\s+(\w+)", text1_lower)
            for word in negated:
                if word in text2_lower and 'not ' not in text2_lower:
                    return True, f"Negation conflict on '{word}'"

        return False, ""

    def detect_complement(self, text1: str, text2: str, domain1: str,
                         domain2: str) -> Tuple[bool, str]:
        """
        Detect if two heuristics might complement each other.

        Returns:
            (is_complement, reason)
        """
        # Same domain is a strong complement signal
        if domain1 == domain2:
            keywords1 = self.extract_keywords(text1)
            keywords2 = self.extract_keywords(text2)

            # Check for shared technical terms
            overlap = keywords1 & keywords2
            if len(overlap) >= 2:
                return True, f"Same domain with shared concepts: {', '.join(list(overlap)[:3])}"

        # Check for complement indicators
        combined = (text1 + " " + text2).lower()
        for indicator in COMPLEMENT_INDICATORS:
            if indicator in combined:
                return True, f"Complement indicator: '{indicator}'"

        return False, ""

    def analyze_heuristic_pair(self, h1: Dict, h2: Dict) -> List[RelationshipCandidate]:
        """
        Analyze a pair of heuristics for potential relationships.

        Returns:
            List of relationship candidates
        """
        candidates = []

        text1 = f"{h1['rule']} {h1.get('explanation', '')}"
        text2 = f"{h2['rule']} {h2.get('explanation', '')}"

        keywords1 = self.extract_keywords(text1)
        keywords2 = self.extract_keywords(text2)

        # Calculate similarity
        similarity = self.jaccard_similarity(keywords1, keywords2)

        # Check for similarity relationship
        if similarity >= SIMILARITY_THRESHOLD:
            candidates.append(RelationshipCandidate(
                heuristic_id_1=h1['id'],
                heuristic_id_2=h2['id'],
                relationship_type='SIMILAR_TO',
                score=similarity,
                reason=f"Keyword similarity: {similarity:.2f}"
            ))

        # Check for conflict
        is_conflict, conflict_reason = self.detect_conflict(text1, text2)
        if is_conflict:
            # Conflict score based on similarity (more similar = more conflicting)
            conflict_score = 0.5 + (similarity * 0.5)
            if conflict_score >= CONFLICT_THRESHOLD:
                candidates.append(RelationshipCandidate(
                    heuristic_id_1=h1['id'],
                    heuristic_id_2=h2['id'],
                    relationship_type='CONFLICTS_WITH',
                    score=conflict_score,
                    reason=conflict_reason
                ))

        # Check for complement
        is_complement, complement_reason = self.detect_complement(
            text1, text2,
            h1.get('domain', ''), h2.get('domain', '')
        )
        if is_complement and not is_conflict:
            complement_score = 0.3 + (similarity * 0.4)
            if complement_score >= COMPLEMENT_THRESHOLD:
                candidates.append(RelationshipCandidate(
                    heuristic_id_1=h1['id'],
                    heuristic_id_2=h2['id'],
                    relationship_type='COMPLEMENTS',
                    score=complement_score,
                    reason=complement_reason
                ))

        return candidates

    def detect_all_relationships(self, domain: str = None) -> List[RelationshipCandidate]:
        """
        Detect relationships between all heuristics.

        Args:
            domain: Optional domain to limit analysis

        Returns:
            List of all detected relationship candidates
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            if domain:
                cursor.execute("""
                    SELECT id, rule, explanation, domain, confidence
                    FROM heuristics
                    WHERE domain = ? AND rule IS NOT NULL
                """, (domain,))
            else:
                cursor.execute("""
                    SELECT id, rule, explanation, domain, confidence
                    FROM heuristics
                    WHERE rule IS NOT NULL
                """)

            heuristics = [dict(row) for row in cursor.fetchall()]
            conn.close()

            logger.info(f"Analyzing {len(heuristics)} heuristics for relationships")

            all_candidates = []

            # Compare each pair
            for i, h1 in enumerate(heuristics):
                for h2 in heuristics[i + 1:]:
                    candidates = self.analyze_heuristic_pair(h1, h2)
                    all_candidates.extend(candidates)

            # Sort by score descending
            all_candidates.sort(key=lambda c: c.score, reverse=True)

            logger.info(f"Found {len(all_candidates)} relationship candidates")
            return all_candidates

        except Exception as e:
            logger.error(f"Error detecting relationships: {e}")
            return []

    def apply_relationships_to_graph(self, candidates: List[RelationshipCandidate] = None,
                                     min_score: float = 0.4) -> Dict:
        """
        Apply detected relationships to the graph database.

        Args:
            candidates: Optional list of candidates (will detect if not provided)
            min_score: Minimum score to apply relationship

        Returns:
            Dict with application statistics
        """
        if not self.graph.is_available:
            return {'status': 'skipped', 'reason': 'graph_unavailable'}

        if candidates is None:
            candidates = self.detect_all_relationships()

        stats = {
            'similar_to': 0,
            'complements': 0,
            'conflicts_with': 0,
            'skipped': 0,
            'errors': 0
        }

        for candidate in candidates:
            if candidate.score < min_score:
                stats['skipped'] += 1
                continue

            try:
                success = False
                if candidate.relationship_type == 'SIMILAR_TO':
                    success = self.graph.add_similar_to(
                        candidate.heuristic_id_1,
                        candidate.heuristic_id_2,
                        candidate.score
                    )
                    if success:
                        stats['similar_to'] += 1

                elif candidate.relationship_type == 'COMPLEMENTS':
                    success = self.graph.add_complements(
                        candidate.heuristic_id_1,
                        candidate.heuristic_id_2
                    )
                    if success:
                        stats['complements'] += 1

                elif candidate.relationship_type == 'CONFLICTS_WITH':
                    success = self.graph.add_conflicts_with(
                        candidate.heuristic_id_1,
                        candidate.heuristic_id_2
                    )
                    if success:
                        stats['conflicts_with'] += 1

            except Exception as e:
                logger.error(f"Error applying relationship: {e}")
                stats['errors'] += 1

        return {
            'status': 'success',
            'stats': stats
        }

    def find_related_for_heuristic(self, heuristic_id: int) -> List[RelationshipCandidate]:
        """
        Find potential relationships for a specific heuristic.

        Args:
            heuristic_id: ID of the heuristic to analyze

        Returns:
            List of relationship candidates involving this heuristic
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            # Get the target heuristic
            cursor.execute("""
                SELECT id, rule, explanation, domain, confidence
                FROM heuristics
                WHERE id = ?
            """, (heuristic_id,))

            target = cursor.fetchone()
            if not target:
                return []

            target = dict(target)

            # Get other heuristics (same domain first, then others)
            cursor.execute("""
                SELECT id, rule, explanation, domain, confidence
                FROM heuristics
                WHERE id != ? AND rule IS NOT NULL
                ORDER BY CASE WHEN domain = ? THEN 0 ELSE 1 END, id
                LIMIT 100
            """, (heuristic_id, target.get('domain', '')))

            others = [dict(row) for row in cursor.fetchall()]
            conn.close()

            all_candidates = []
            for other in others:
                candidates = self.analyze_heuristic_pair(target, other)
                all_candidates.extend(candidates)

            all_candidates.sort(key=lambda c: c.score, reverse=True)
            return all_candidates

        except Exception as e:
            logger.error(f"Error finding related heuristics: {e}")
            return []


# Singleton instance
_detector: Optional[RelationshipDetector] = None


def get_relationship_detector() -> RelationshipDetector:
    """Get the singleton detector instance."""
    global _detector
    if _detector is None:
        _detector = RelationshipDetector()
    return _detector


def detect_and_apply_relationships(domain: str = None, min_score: float = 0.4) -> Dict:
    """
    Detect and apply all relationships.

    Convenience function for one-shot relationship detection.
    """
    detector = get_relationship_detector()
    candidates = detector.detect_all_relationships(domain)
    return detector.apply_relationships_to_graph(candidates, min_score)


# For testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    detector = get_relationship_detector()

    # Detect relationships
    candidates = detector.detect_all_relationships()

    print(f"\nFound {len(candidates)} relationship candidates:\n")

    # Show top 10
    for candidate in candidates[:10]:
        print(f"  {candidate.heuristic_id_1} <--> {candidate.heuristic_id_2}")
        print(f"    Type: {candidate.relationship_type}")
        print(f"    Score: {candidate.score:.2f}")
        print(f"    Reason: {candidate.reason}")
        print()

    # Apply to graph if available
    if detector.graph.is_available:
        result = detector.apply_relationships_to_graph(candidates)
        print(f"\nApplied to graph: {result}")
    else:
        print("\nGraph database not available")
        print("Start FalkorDB with: docker-compose up -d")
