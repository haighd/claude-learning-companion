#!/usr/bin/env python3
"""
Graph Store: FalkorDB interface for semantic relationships.

Provides a graph database layer on top of SQLite for:
- Semantic relationships between heuristics
- Conflict detection
- Similarity queries
- Knowledge graph visualization

Part of the Auto-Claude Integration (P3: Graph-Based Memory).
"""

import logging
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

# Try to import redis/falkordb
try:
    import redis
    from redis.commands.graph import Graph
    FALKORDB_AVAILABLE = True
except ImportError:
    FALKORDB_AVAILABLE = False
    Graph = None

logger = logging.getLogger(__name__)

# Configuration
FALKORDB_HOST = "localhost"
FALKORDB_PORT = 6379
GRAPH_NAME = "clc_knowledge"


@dataclass
class GraphNode:
    """Represents a node in the knowledge graph."""
    id: str
    label: str  # Heuristic, GoldenRule, Failure, Success, Domain
    properties: Dict[str, Any]


@dataclass
class GraphEdge:
    """Represents an edge in the knowledge graph."""
    source_id: str
    target_id: str
    relationship: str  # DERIVED_FROM, VALIDATED_BY, CONFLICTS_WITH, etc.
    properties: Dict[str, Any]


@dataclass
class GraphQueryResult:
    """Result from a graph query."""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    raw_result: Any = None


class GraphStore:
    """
    FalkorDB interface for CLC knowledge graph.

    Provides graceful fallback when FalkorDB is unavailable.
    """

    def __init__(self, host: str = FALKORDB_HOST, port: int = FALKORDB_PORT,
                 graph_name: str = GRAPH_NAME):
        self.host = host
        self.port = port
        self.graph_name = graph_name
        self._client: Optional[redis.Redis] = None
        self._graph: Optional[Graph] = None
        self._connected = False
        self._pending_operations: List[Dict] = []

    @property
    def is_available(self) -> bool:
        """Check if FalkorDB is available."""
        if not FALKORDB_AVAILABLE:
            return False
        return self._connected

    def connect(self) -> bool:
        """Connect to FalkorDB."""
        if not FALKORDB_AVAILABLE:
            logger.warning("FalkorDB client not installed. Install with: pip install redis")
            return False

        try:
            self._client = redis.Redis(host=self.host, port=self.port, decode_responses=True)
            self._client.ping()
            self._graph = self._client.graph(self.graph_name)
            self._connected = True
            logger.info(f"Connected to FalkorDB at {self.host}:{self.port}")

            # Process any pending operations
            self._process_pending_operations()

            return True
        except redis.ConnectionError as e:
            logger.warning(f"Could not connect to FalkorDB: {e}")
            self._connected = False
            return False
        except Exception as e:
            logger.error(f"Error connecting to FalkorDB: {e}")
            self._connected = False
            return False

    def disconnect(self):
        """Disconnect from FalkorDB."""
        if self._client:
            self._client.close()
            self._client = None
            self._graph = None
            self._connected = False

    def ensure_schema(self):
        """Create indexes and constraints for the graph schema."""
        if not self.is_available:
            return

        try:
            # Create indexes for faster lookups
            indexes = [
                "CREATE INDEX IF NOT EXISTS FOR (h:Heuristic) ON (h.id)",
                "CREATE INDEX IF NOT EXISTS FOR (h:Heuristic) ON (h.domain)",
                "CREATE INDEX IF NOT EXISTS FOR (g:GoldenRule) ON (g.id)",
                "CREATE INDEX IF NOT EXISTS FOR (f:Failure) ON (f.id)",
                "CREATE INDEX IF NOT EXISTS FOR (s:Success) ON (s.id)",
                "CREATE INDEX IF NOT EXISTS FOR (d:Domain) ON (d.name)",
            ]

            for index_query in indexes:
                try:
                    self._graph.query(index_query)
                except Exception:
                    pass  # Index may already exist

            logger.info("Graph schema indexes created/verified")
        except Exception as e:
            logger.error(f"Error creating schema: {e}")

    # === NODE OPERATIONS ===

    def create_heuristic_node(self, heuristic_id: int, content: str,
                              domain: str, confidence: float) -> bool:
        """Create a Heuristic node in the graph."""
        if not self.is_available:
            self._queue_operation('create_heuristic_node', {
                'heuristic_id': heuristic_id,
                'content': content,
                'domain': domain,
                'confidence': confidence
            })
            return False

        try:
            query = """
                MERGE (h:Heuristic {id: $id})
                SET h.content = $content,
                    h.domain = $domain,
                    h.confidence = $confidence
                RETURN h
            """
            self._graph.query(query, {
                'id': str(heuristic_id),
                'content': content[:500],  # Limit content size
                'domain': domain,
                'confidence': confidence
            })

            # Also create/link to domain node
            self._ensure_domain_node(domain)
            self._create_relationship(
                str(heuristic_id), 'Heuristic',
                domain, 'Domain',
                'BELONGS_TO'
            )

            return True
        except Exception as e:
            logger.error(f"Error creating heuristic node: {e}")
            return False

    def create_golden_rule_node(self, rule_id: int, content: str, domain: str) -> bool:
        """Create a GoldenRule node in the graph."""
        if not self.is_available:
            self._queue_operation('create_golden_rule_node', {
                'rule_id': rule_id,
                'content': content,
                'domain': domain
            })
            return False

        try:
            query = """
                MERGE (g:GoldenRule {id: $id})
                SET g.content = $content,
                    g.domain = $domain
                RETURN g
            """
            self._graph.query(query, {
                'id': str(rule_id),
                'content': content[:500],
                'domain': domain
            })
            return True
        except Exception as e:
            logger.error(f"Error creating golden rule node: {e}")
            return False

    def create_failure_node(self, failure_id: str, description: str,
                           root_cause: str = None) -> bool:
        """Create a Failure node in the graph."""
        if not self.is_available:
            return False

        try:
            query = """
                MERGE (f:Failure {id: $id})
                SET f.description = $description,
                    f.root_cause = $root_cause
                RETURN f
            """
            self._graph.query(query, {
                'id': failure_id,
                'description': description[:500],
                'root_cause': root_cause or ''
            })
            return True
        except Exception as e:
            logger.error(f"Error creating failure node: {e}")
            return False

    def create_success_node(self, success_id: str, description: str,
                           approach: str = None) -> bool:
        """Create a Success node in the graph."""
        if not self.is_available:
            return False

        try:
            query = """
                MERGE (s:Success {id: $id})
                SET s.description = $description,
                    s.approach = $approach
                RETURN s
            """
            self._graph.query(query, {
                'id': success_id,
                'description': description[:500],
                'approach': approach or ''
            })
            return True
        except Exception as e:
            logger.error(f"Error creating success node: {e}")
            return False

    def _ensure_domain_node(self, domain: str) -> bool:
        """Ensure a Domain node exists."""
        if not self.is_available:
            return False

        try:
            query = """
                MERGE (d:Domain {name: $name})
                RETURN d
            """
            self._graph.query(query, {'name': domain})
            return True
        except Exception as e:
            logger.error(f"Error creating domain node: {e}")
            return False

    # === RELATIONSHIP OPERATIONS ===

    def _create_relationship(self, source_id: str, source_label: str,
                            target_id: str, target_label: str,
                            relationship: str, properties: Dict = None) -> bool:
        """Create a relationship between two nodes."""
        if not self.is_available:
            return False

        try:
            props_str = ""
            if properties:
                props_list = [f"{k}: ${k}" for k in properties.keys()]
                props_str = " {" + ", ".join(props_list) + "}"

            query = f"""
                MATCH (a:{source_label} {{id: $source_id}})
                MATCH (b:{target_label} {{{'id' if target_label != 'Domain' else 'name'}: $target_id}})
                MERGE (a)-[r:{relationship}{props_str}]->(b)
                RETURN r
            """
            params = {
                'source_id': source_id,
                'target_id': target_id,
                **(properties or {})
            }
            self._graph.query(query, params)
            return True
        except Exception as e:
            logger.error(f"Error creating relationship: {e}")
            return False

    def add_derived_from(self, heuristic_id: int, failure_id: str) -> bool:
        """Link a heuristic to its source failure."""
        return self._create_relationship(
            str(heuristic_id), 'Heuristic',
            failure_id, 'Failure',
            'DERIVED_FROM'
        )

    def add_validated_by(self, heuristic_id: int, success_id: str) -> bool:
        """Link a heuristic to a validating success."""
        return self._create_relationship(
            str(heuristic_id), 'Heuristic',
            success_id, 'Success',
            'VALIDATED_BY'
        )

    def add_conflicts_with(self, heuristic_id_1: int, heuristic_id_2: int) -> bool:
        """Mark two heuristics as conflicting."""
        return self._create_relationship(
            str(heuristic_id_1), 'Heuristic',
            str(heuristic_id_2), 'Heuristic',
            'CONFLICTS_WITH'
        )

    def add_complements(self, heuristic_id_1: int, heuristic_id_2: int) -> bool:
        """Mark two heuristics as complementary."""
        return self._create_relationship(
            str(heuristic_id_1), 'Heuristic',
            str(heuristic_id_2), 'Heuristic',
            'COMPLEMENTS'
        )

    def add_similar_to(self, heuristic_id_1: int, heuristic_id_2: int,
                       score: float) -> bool:
        """Mark two heuristics as similar with a score."""
        return self._create_relationship(
            str(heuristic_id_1), 'Heuristic',
            str(heuristic_id_2), 'Heuristic',
            'SIMILAR_TO',
            {'score': score}
        )

    def add_promoted_from(self, golden_rule_id: int, heuristic_id: int) -> bool:
        """Link a golden rule to its source heuristic."""
        return self._create_relationship(
            str(golden_rule_id), 'GoldenRule',
            str(heuristic_id), 'Heuristic',
            'PROMOTED_FROM'
        )

    # === QUERY OPERATIONS ===

    def get_related_heuristics(self, heuristic_id: int,
                               max_depth: int = 2) -> List[Dict]:
        """Get heuristics related to the given one."""
        if not self.is_available:
            return []

        try:
            query = f"""
                MATCH (h:Heuristic {{id: $id}})-[:COMPLEMENTS|SIMILAR_TO*1..{max_depth}]-(related:Heuristic)
                WHERE related.id <> $id
                RETURN DISTINCT related.id as id,
                       related.content as content,
                       related.domain as domain,
                       related.confidence as confidence
            """
            result = self._graph.query(query, {'id': str(heuristic_id)})

            return [
                {
                    'id': int(row[0]),
                    'content': row[1],
                    'domain': row[2],
                    'confidence': row[3]
                }
                for row in result.result_set
            ]
        except Exception as e:
            logger.error(f"Error getting related heuristics: {e}")
            return []

    def get_conflicting_heuristics(self, domain: str = None) -> List[Tuple[Dict, Dict]]:
        """Get pairs of conflicting heuristics."""
        if not self.is_available:
            return []

        try:
            if domain:
                query = """
                    MATCH (h1:Heuristic)-[:CONFLICTS_WITH]-(h2:Heuristic)
                    WHERE h1.domain = $domain AND h2.domain = $domain
                    AND id(h1) < id(h2)
                    RETURN h1.id, h1.content, h1.domain,
                           h2.id, h2.content, h2.domain
                """
                result = self._graph.query(query, {'domain': domain})
            else:
                query = """
                    MATCH (h1:Heuristic)-[:CONFLICTS_WITH]-(h2:Heuristic)
                    WHERE id(h1) < id(h2)
                    RETURN h1.id, h1.content, h1.domain,
                           h2.id, h2.content, h2.domain
                """
                result = self._graph.query(query)

            return [
                (
                    {'id': int(row[0]), 'content': row[1], 'domain': row[2]},
                    {'id': int(row[3]), 'content': row[4], 'domain': row[5]}
                )
                for row in result.result_set
            ]
        except Exception as e:
            logger.error(f"Error getting conflicting heuristics: {e}")
            return []

    def get_knowledge_graph_data(self, limit: int = 100) -> GraphQueryResult:
        """Get data for knowledge graph visualization."""
        if not self.is_available:
            return GraphQueryResult(nodes=[], edges=[])

        try:
            # Get nodes
            node_query = """
                MATCH (n)
                WHERE n:Heuristic OR n:GoldenRule OR n:Domain
                RETURN labels(n)[0] as label,
                       CASE WHEN n:Domain THEN n.name ELSE n.id END as id,
                       properties(n) as props
                LIMIT $limit
            """
            node_result = self._graph.query(node_query, {'limit': limit})

            nodes = [
                GraphNode(
                    id=str(row[1]),
                    label=row[0],
                    properties=row[2] if row[2] else {}
                )
                for row in node_result.result_set
            ]

            # Get edges
            edge_query = """
                MATCH (a)-[r]->(b)
                WHERE (a:Heuristic OR a:GoldenRule) AND (b:Heuristic OR b:GoldenRule OR b:Domain)
                RETURN CASE WHEN a:Domain THEN a.name ELSE a.id END as source,
                       CASE WHEN b:Domain THEN b.name ELSE b.id END as target,
                       type(r) as relationship,
                       properties(r) as props
                LIMIT $limit
            """
            edge_result = self._graph.query(edge_query, {'limit': limit})

            edges = [
                GraphEdge(
                    source_id=str(row[0]),
                    target_id=str(row[1]),
                    relationship=row[2],
                    properties=row[3] if row[3] else {}
                )
                for row in edge_result.result_set
            ]

            return GraphQueryResult(nodes=nodes, edges=edges)
        except Exception as e:
            logger.error(f"Error getting knowledge graph data: {e}")
            return GraphQueryResult(nodes=[], edges=[])

    def get_heuristics_by_domain(self, domain: str) -> List[Dict]:
        """Get all heuristics for a domain with their relationships."""
        if not self.is_available:
            return []

        try:
            query = """
                MATCH (h:Heuristic)-[:BELONGS_TO]->(d:Domain {name: $domain})
                OPTIONAL MATCH (h)-[r]-(related)
                RETURN h.id, h.content, h.confidence,
                       collect(DISTINCT {type: type(r), target:
                         CASE WHEN related:Domain THEN related.name ELSE related.id END}) as relationships
            """
            result = self._graph.query(query, {'domain': domain})

            return [
                {
                    'id': int(row[0]),
                    'content': row[1],
                    'confidence': row[2],
                    'relationships': row[3]
                }
                for row in result.result_set
            ]
        except Exception as e:
            logger.error(f"Error getting heuristics by domain: {e}")
            return []

    # === STATISTICS ===

    def get_graph_stats(self) -> Dict:
        """Get statistics about the graph."""
        if not self.is_available:
            return {
                'available': False,
                'pending_operations': len(self._pending_operations)
            }

        try:
            stats_query = """
                MATCH (n)
                RETURN labels(n)[0] as label, count(n) as count
            """
            node_stats = self._graph.query(stats_query)

            edge_query = """
                MATCH ()-[r]->()
                RETURN type(r) as type, count(r) as count
            """
            edge_stats = self._graph.query(edge_query)

            return {
                'available': True,
                'nodes': {row[0]: row[1] for row in node_stats.result_set},
                'edges': {row[0]: row[1] for row in edge_stats.result_set},
                'pending_operations': len(self._pending_operations)
            }
        except Exception as e:
            logger.error(f"Error getting graph stats: {e}")
            return {'available': True, 'error': str(e)}

    # === PENDING OPERATIONS ===

    def _queue_operation(self, operation: str, params: Dict):
        """Queue an operation for later when graph becomes available."""
        self._pending_operations.append({
            'operation': operation,
            'params': params
        })
        # Keep queue bounded
        if len(self._pending_operations) > 1000:
            self._pending_operations = self._pending_operations[-500:]

    def _process_pending_operations(self):
        """Process queued operations after reconnecting."""
        if not self._pending_operations:
            return

        logger.info(f"Processing {len(self._pending_operations)} pending graph operations")

        processed = 0
        for op in self._pending_operations:
            try:
                method = getattr(self, op['operation'], None)
                if method:
                    method(**op['params'])
                    processed += 1
            except Exception as e:
                logger.error(f"Error processing pending operation: {e}")

        logger.info(f"Processed {processed}/{len(self._pending_operations)} pending operations")
        self._pending_operations = []


# Singleton instance
_graph_store: Optional[GraphStore] = None


def get_graph_store() -> GraphStore:
    """Get the singleton graph store instance."""
    global _graph_store
    if _graph_store is None:
        _graph_store = GraphStore()
        _graph_store.connect()
        if _graph_store.is_available:
            _graph_store.ensure_schema()
    return _graph_store


# For testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    store = get_graph_store()
    print(f"FalkorDB available: {store.is_available}")
    print(f"Graph stats: {store.get_graph_stats()}")

    if store.is_available:
        # Test creating nodes
        store.create_heuristic_node(1, "Test heuristic", "test", 0.8)
        store.create_heuristic_node(2, "Related heuristic", "test", 0.7)
        store.add_complements(1, 2)

        # Test querying
        related = store.get_related_heuristics(1)
        print(f"Related to heuristic 1: {related}")

        # Get visualization data
        graph_data = store.get_knowledge_graph_data()
        print(f"Graph has {len(graph_data.nodes)} nodes and {len(graph_data.edges)} edges")
