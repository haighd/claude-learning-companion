"""
Graph Router - Knowledge graph queries and visualization.

Provides API endpoints for:
- Graph statistics
- Knowledge graph data for visualization
- Related heuristics queries
- Conflict detection

Part of Auto-Claude Integration (P3: Graph-Based Memory).
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/graph", tags=["graph"])
logger = logging.getLogger(__name__)

# Path to CLC for importing graph_store
CLC_PATH: Optional[Path] = None


def set_paths(clc_path: Path):
    """Set the paths for graph operations."""
    global CLC_PATH
    CLC_PATH = clc_path


def _get_graph_store():
    """Get the graph store, dynamically importing from CLC."""
    if CLC_PATH is None:
        return None

    try:
        memory_path = CLC_PATH / "memory"
        if str(memory_path) not in sys.path:
            sys.path.insert(0, str(memory_path))

        from graph_store import get_graph_store
        return get_graph_store()
    except ImportError as e:
        logger.warning(f"Could not import graph_store: {e}")
        return None
    except Exception as e:
        logger.error(f"Error getting graph store: {e}")
        return None


def _get_fallback_data():
    """Get data from SQLite when graph is unavailable."""
    try:
        backend_path = Path(__file__).parent.parent
        if str(backend_path) not in sys.path:
            sys.path.insert(0, str(backend_path))

        from utils import get_db, dict_from_row

        with get_db() as conn:
            cursor = conn.cursor()

            # Get heuristics as nodes (including golden rules which have is_golden=1)
            cursor.execute("""
                SELECT id, domain, rule, confidence, is_golden
                FROM heuristics
                ORDER BY is_golden DESC, confidence DESC
                LIMIT 100
            """)
            heuristics = [dict_from_row(r) for r in cursor.fetchall()]

            # Build nodes - separate golden rules from regular heuristics
            nodes = []
            for h in heuristics:
                label = "GoldenRule" if h["is_golden"] else "Heuristic"
                nodes.append({
                    "id": f"h_{h['id']}",
                    "label": label,
                    "properties": {
                        "content": h["rule"][:200] if h["rule"] else "",
                        "domain": h["domain"],
                        "confidence": h["confidence"],
                        "is_golden": h["is_golden"]
                    }
                })

            # Get unique domains
            domains = set()
            for h in heuristics:
                if h["domain"]:
                    domains.add(h["domain"])

            for domain in domains:
                nodes.append({
                    "id": f"d_{domain}",
                    "label": "Domain",
                    "properties": {"name": domain}
                })

            # Build edges (heuristic -> domain)
            edges = []
            for h in heuristics:
                if h["domain"]:
                    edges.append({
                        "source_id": f"h_{h['id']}",
                        "target_id": f"d_{h['domain']}",
                        "relationship": "BELONGS_TO",
                        "properties": {}
                    })

            return {
                "nodes": nodes,
                "edges": edges,
                "source": "sqlite_fallback"
            }
    except Exception as e:
        logger.error(f"Error getting fallback data: {e}")
        return {"nodes": [], "edges": [], "source": "error", "error": str(e)}


@router.get("/stats")
async def get_graph_stats():
    """
    Get statistics about the knowledge graph.

    Returns node counts by type, edge counts by relationship,
    and connection status.
    """
    store = _get_graph_store()

    if store is None:
        # Return SQLite-based stats
        try:
            backend_path = Path(__file__).parent.parent
            if str(backend_path) not in sys.path:
                sys.path.insert(0, str(backend_path))

            from utils import get_db

            with get_db() as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT COUNT(*) FROM heuristics WHERE is_golden = 0")
                heuristic_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM heuristics WHERE is_golden = 1")
                golden_rule_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(DISTINCT domain) FROM heuristics")
                domain_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM learnings")
                learning_count = cursor.fetchone()[0]

                return {
                    "available": False,
                    "source": "sqlite",
                    "nodes": {
                        "Heuristic": heuristic_count,
                        "GoldenRule": golden_rule_count,
                        "Domain": domain_count,
                        "Learning": learning_count
                    },
                    "edges": {},
                    "pending_operations": 0,
                    "message": "FalkorDB not available, showing SQLite counts"
                }
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
                "nodes": {},
                "edges": {}
            }

    return store.get_graph_stats()


@router.get("/knowledge-graph")
async def get_knowledge_graph(
    limit: int = Query(100, ge=1, le=500, description="Max nodes to return")
):
    """
    Get knowledge graph data for visualization.

    Returns nodes and edges suitable for rendering with a graph
    visualization library (D3, vis.js, cytoscape, etc.).
    """
    store = _get_graph_store()

    if store is None or not store.is_available:
        # Return SQLite-based graph data
        fallback = _get_fallback_data()
        return {
            "nodes": fallback["nodes"][:limit],
            "edges": fallback["edges"],
            "source": fallback.get("source", "sqlite_fallback"),
            "falkordb_available": False
        }

    try:
        result = store.get_knowledge_graph_data(limit=limit)

        nodes = [
            {
                "id": node.id,
                "label": node.label,
                "properties": node.properties
            }
            for node in result.nodes
        ]

        edges = [
            {
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "relationship": edge.relationship,
                "properties": edge.properties
            }
            for edge in result.edges
        ]

        return {
            "nodes": nodes,
            "edges": edges,
            "source": "falkordb",
            "falkordb_available": True
        }
    except Exception as e:
        logger.error(f"Error getting knowledge graph: {e}")
        fallback = _get_fallback_data()
        return {
            "nodes": fallback["nodes"][:limit],
            "edges": fallback["edges"],
            "source": "sqlite_fallback_on_error",
            "error": str(e),
            "falkordb_available": False
        }


@router.get("/related/{heuristic_id}")
async def get_related_heuristics(
    heuristic_id: int,
    max_depth: int = Query(2, ge=1, le=4, description="Max relationship depth")
):
    """
    Get heuristics related to the given one.

    Finds heuristics connected via COMPLEMENTS or SIMILAR_TO
    relationships up to max_depth hops away.
    """
    store = _get_graph_store()

    if store is None or not store.is_available:
        # Fallback: find heuristics in same domain from SQLite
        try:
            backend_path = Path(__file__).parent.parent
            if str(backend_path) not in sys.path:
                sys.path.insert(0, str(backend_path))

            from utils import get_db, dict_from_row

            with get_db() as conn:
                cursor = conn.cursor()

                # Get the source heuristic's domain
                cursor.execute(
                    "SELECT domain FROM heuristics WHERE id = ?",
                    (heuristic_id,)
                )
                row = cursor.fetchone()
                if not row:
                    return {
                        "heuristic_id": heuristic_id,
                        "related": [],
                        "source": "not_found"
                    }

                domain = row[0]

                # Get other heuristics in same domain
                cursor.execute("""
                    SELECT id, domain, rule, confidence
                    FROM heuristics
                    WHERE domain = ? AND id != ?
                    ORDER BY confidence DESC
                    LIMIT 10
                """, (domain, heuristic_id))

                related = [
                    {
                        "id": r[0],
                        "domain": r[1],
                        "content": r[2][:200] if r[2] else "",
                        "confidence": r[3],
                        "relationship": "SAME_DOMAIN"
                    }
                    for r in cursor.fetchall()
                ]

                return {
                    "heuristic_id": heuristic_id,
                    "related": related,
                    "source": "sqlite_fallback"
                }
        except Exception as e:
            logger.error(f"Error getting related heuristics: {e}")
            return {
                "heuristic_id": heuristic_id,
                "related": [],
                "error": str(e)
            }

    try:
        related = store.get_related_heuristics(heuristic_id, max_depth=max_depth)
        return {
            "heuristic_id": heuristic_id,
            "related": related,
            "source": "falkordb"
        }
    except Exception as e:
        logger.error(f"Error getting related heuristics: {e}")
        return {
            "heuristic_id": heuristic_id,
            "related": [],
            "error": str(e)
        }


@router.get("/conflicts")
async def get_conflicting_heuristics(
    domain: Optional[str] = Query(None, description="Filter by domain")
):
    """
    Get pairs of conflicting heuristics.

    Returns heuristics that have been marked as CONFLICTS_WITH
    each other, optionally filtered by domain.
    """
    store = _get_graph_store()

    if store is None or not store.is_available:
        # No conflict detection without graph
        return {
            "conflicts": [],
            "source": "sqlite_fallback",
            "message": "Conflict detection requires FalkorDB"
        }

    try:
        conflicts = store.get_conflicting_heuristics(domain=domain)

        return {
            "conflicts": [
                {
                    "heuristic_1": conflict[0],
                    "heuristic_2": conflict[1]
                }
                for conflict in conflicts
            ],
            "domain_filter": domain,
            "source": "falkordb"
        }
    except Exception as e:
        logger.error(f"Error getting conflicts: {e}")
        return {
            "conflicts": [],
            "error": str(e)
        }


@router.get("/domain/{domain}")
async def get_heuristics_by_domain(domain: str):
    """
    Get all heuristics for a domain with their relationships.

    Returns heuristics belonging to the specified domain along
    with their graph relationships.
    """
    store = _get_graph_store()

    if store is None or not store.is_available:
        # Fallback to SQLite
        try:
            backend_path = Path(__file__).parent.parent
            if str(backend_path) not in sys.path:
                sys.path.insert(0, str(backend_path))

            from utils import get_db, dict_from_row

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, domain, rule, confidence, is_golden
                    FROM heuristics
                    WHERE domain = ?
                    ORDER BY confidence DESC
                """, (domain,))

                heuristics = [
                    {
                        "id": r[0],
                        "domain": r[1],
                        "content": r[2][:200] if r[2] else "",
                        "confidence": r[3],
                        "is_golden": r[4],
                        "relationships": []
                    }
                    for r in cursor.fetchall()
                ]

                return {
                    "domain": domain,
                    "heuristics": heuristics,
                    "source": "sqlite_fallback"
                }
        except Exception as e:
            logger.error(f"Error getting domain heuristics: {e}")
            return {
                "domain": domain,
                "heuristics": [],
                "error": str(e)
            }

    try:
        heuristics = store.get_heuristics_by_domain(domain)
        return {
            "domain": domain,
            "heuristics": heuristics,
            "source": "falkordb"
        }
    except Exception as e:
        logger.error(f"Error getting domain heuristics: {e}")
        return {
            "domain": domain,
            "heuristics": [],
            "error": str(e)
        }


@router.post("/sync")
async def trigger_graph_sync():
    """
    Trigger a sync from SQLite to FalkorDB.

    This endpoint manually triggers the graph sync process,
    useful after bulk data imports or when graph is out of sync.
    """
    if CLC_PATH is None:
        return {
            "success": False,
            "message": "CLC path not configured"
        }

    try:
        memory_path = CLC_PATH / "memory"
        if str(memory_path) not in sys.path:
            sys.path.insert(0, str(memory_path))

        from graph_sync import GraphSync

        sync = GraphSync()
        result = sync.sync_all()

        return {
            "success": True,
            "result": result
        }
    except ImportError:
        return {
            "success": False,
            "message": "graph_sync module not available"
        }
    except Exception as e:
        logger.error(f"Error triggering graph sync: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/health")
async def graph_health():
    """
    Check health of graph database connection.

    Returns connection status and basic diagnostics.
    """
    store = _get_graph_store()

    if store is None:
        return {
            "status": "unavailable",
            "reason": "graph_store not importable",
            "fallback": "sqlite"
        }

    if not store.is_available:
        return {
            "status": "disconnected",
            "reason": "FalkorDB not connected",
            "fallback": "sqlite",
            "pending_operations": len(store._pending_operations)
        }

    try:
        stats = store.get_graph_stats()
        return {
            "status": "healthy",
            "connected": True,
            "stats": stats
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "fallback": "sqlite"
        }
