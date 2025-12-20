# Graph Memory Setup Guide

## Overview

The knowledge graph provides semantic relationships between heuristics, failures, and learnings in the Claude Learning Companion (CLC) system.

**Key Features:**
- Semantic similarity detection between heuristics
- Conflict detection (opposing rules)
- Complementary relationship identification
- 3D cosmic knowledge graph visualization
- Real-time relationship discovery

## Architecture

```
┌─────────────────┐
│  SQLite DB      │  ← Primary source of truth
│  (index.db)     │  ← Always available (fallback mode)
└────────┬────────┘
         │
         │ sync
         ↓
┌─────────────────┐
│  FalkorDB       │  ← Optional graph layer
│  (port 6379)    │  ← Provides relationship queries
└────────┬────────┘
         │
         │ powers
         ↓
┌─────────────────┐
│  Dashboard      │  ← 3D visualization
│  Graph View     │  ← Relationship exploration
└─────────────────┘
```

**Components:**
- **Primary Store:** SQLite (`memory/index.db`) - always available
- **Graph Store:** FalkorDB (Redis-compatible) - optional enhancement
- **Sync Service:** Background process that keeps them synchronized
- **Relationship Detector:** Auto-discovers semantic connections
- **Visualization:** 3D cosmic graph in the dashboard

## Installation (Optional)

**FalkorDB is completely optional.** The system works perfectly with SQLite alone.

### Benefits of Enabling FalkorDB

- Visual exploration of knowledge relationships
- Faster semantic similarity queries
- Conflict detection across heuristics
- Path finding between related concepts
- 3D graph visualization

### Prerequisites

```bash
# 1. Docker (for running FalkorDB)
docker --version

# 2. Python Redis client
pip install redis
```

### Setup Steps

#### 1. Start FalkorDB Container

```bash
# Using docker run (simplest)
docker run -d \
  --name clc-falkordb \
  -p 6379:6379 \
  -v falkordb-data:/var/lib/falkordb \
  --restart unless-stopped \
  falkordb/falkordb:latest
```

**Or using docker-compose:**

Create `docker-compose.yml`:

```yaml
version: '3.8'
services:
  falkordb:
    image: falkordb/falkordb:latest
    container_name: clc-falkordb
    ports:
      - "6379:6379"
    volumes:
      - falkordb-data:/var/lib/falkordb
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

volumes:
  falkordb-data:
```

Then run:

```bash
docker-compose up -d falkordb
```

#### 2. Verify FalkorDB is Running

```bash
# Check container status
docker ps | grep falkordb

# Test connection
redis-cli ping
# Should return: PONG
```

#### 3. Perform Initial Sync

```bash
# Option A: Via API (dashboard must be running)
curl -X POST http://localhost:8000/api/graph/sync

# Option B: Start background sync service
bash ~/.claude/clc/scripts/start-graph-sync.sh
```

#### 4. Verify Graph is Populated

```bash
# Check health endpoint
curl http://localhost:8000/api/graph/health

# Should return:
# {
#   "status": "healthy",
#   "connected": true,
#   "nodes": 150,
#   "edges": 78
# }
```

## Usage

### Background Sync Service

The sync service keeps SQLite and FalkorDB in sync automatically.

**Start the service:**

```bash
# Default: sync every 5 minutes
bash ~/.claude/clc/scripts/start-graph-sync.sh

# Custom interval: sync every 10 minutes
python3 -m memory.graph_sync_service --interval 600

# Skip initial full sync on startup
python3 -m memory.graph_sync_service --no-initial-sync
```

**Stop the service:**

```bash
# Send SIGTERM or SIGINT
pkill -f graph_sync_service

# Or use Ctrl+C if running in foreground
```

### Manual Sync Operations

**Full sync (all data):**

```bash
# Via API
curl -X POST http://localhost:8000/api/graph/sync

# Via Python
python3 << EOF
from memory.graph_sync import GraphSync
sync = GraphSync()
result = sync.full_sync()
print(result)
EOF
```

**Sync single heuristic:**

```python
from memory.graph_sync import GraphSync
sync = GraphSync()
sync.sync_heuristic(heuristic_id=123)
```

### Querying Relationships

**Find similar heuristics:**

```bash
curl http://localhost:8000/api/graph/heuristics/123/related?limit=5
```

**Detect conflicts:**

```bash
curl http://localhost:8000/api/graph/heuristics/123/conflicts
```

**Get graph statistics:**

```bash
curl http://localhost:8000/api/graph/stats
```

## Automatic Features

When FalkorDB is enabled, the following happen automatically:

### On Heuristic Creation

1. **Heuristic is added to SQLite** (always)
2. **Relationship detection runs** (if FalkorDB available)
   - Compares against existing heuristics
   - Detects similar, complementary, or conflicting patterns
   - Creates edges in the graph
3. **Kanban task is created** for validation (Issue #32)

### On Heuristic Validation

1. **Confidence score updated** in SQLite
2. **Graph node updated** (if FalkorDB available)
3. **Kanban task moved to done** (Issue #32)

### Background Sync

- Runs every 5 minutes (configurable)
- Syncs any new or updated records
- Gracefully handles FalkorDB unavailability
- Logs sync statistics

## Fallback Behavior

**If FalkorDB is unavailable:**

- ✅ System continues to work normally
- ✅ All data stored in SQLite
- ✅ Heuristics still validated and tracked
- ✅ Kanban tasks still created
- ❌ 3D graph visualization unavailable
- ❌ Semantic relationship queries return empty
- ⚠️  Relationship detection skipped

**The system logs warnings but never fails.**

## Troubleshooting

### FalkorDB Won't Start

```bash
# Check if port 6379 is already in use
lsof -i :6379

# If Redis is running, stop it or use a different port
docker run -d \
  --name clc-falkordb \
  -p 6380:6379 \
  falkordb/falkordb:latest

# Update graph_store.py: FALKORDB_PORT = 6380
```

### Connection Errors in Logs

```
Warning: FalkorDB connection failed (attempt 1/3): [Errno 61] Connection refused
```

**Solutions:**

1. **FalkorDB not running:** `docker ps | grep falkordb`
2. **Wrong host/port:** Check `memory/graph_store.py` configuration
3. **Firewall blocking:** Allow connections on port 6379

### Sync Service Crashes

Check the logs:

```bash
# If running as systemd service
journalctl -u graph-sync -f

# If running manually
python3 -m memory.graph_sync_service --interval 300
```

### Graph is Empty

```bash
# Trigger manual full sync
curl -X POST http://localhost:8000/api/graph/sync

# Check sync result
curl http://localhost:8000/api/graph/stats
```

## Performance Tuning

### For Large Knowledge Bases (>1000 heuristics)

**Increase sync interval:**

```bash
# Sync every 15 minutes instead of 5
python3 -m memory.graph_sync_service --interval 900
```

**Adjust relationship detection thresholds:**

Edit `memory/relationship_detector.py`:

```python
SIMILARITY_THRESHOLD = 0.5  # Increase to reduce false positives
COMPLEMENT_THRESHOLD = 0.4
CONFLICT_THRESHOLD = 0.6
```

### For Real-Time Updates

**Decrease sync interval:**

```bash
# Sync every 2 minutes
python3 -m memory.graph_sync_service --interval 120
```

**Or use event-driven sync** (future enhancement):

Currently, sync is time-based. For instant updates, you would need to trigger `sync_heuristic()` immediately after creation in the hook.

## Advanced Configuration

### Environment Variables

```bash
# FalkorDB connection (optional)
export FALKORDB_HOST=localhost
export FALKORDB_PORT=6379

# Disable graph features entirely
export GRAPH_ENABLED=false
```

### Custom Graph Name

Edit `memory/graph_store.py`:

```python
GRAPH_NAME = "clc_knowledge"  # Change to your preferred name
```

### Relationship Detection

Enable/disable automatic relationship detection in `hooks/clc/core/post_hook.py`:

```python
# Comment out to disable automatic relationship detection
try:
    from memory.relationship_detector import RelationshipDetector
    # ...
except Exception as graph_error:
    pass
```

## Monitoring

### Health Check

```bash
curl http://localhost:8000/api/graph/health
```

**Healthy response:**

```json
{
  "status": "healthy",
  "connected": true,
  "nodes": 150,
  "edges": 78,
  "last_sync": "2025-12-20T10:30:00"
}
```

**Degraded response (FalkorDB down):**

```json
{
  "status": "degraded",
  "connected": false,
  "fallback": "sqlite",
  "message": "FalkorDB unavailable, using SQLite only"
}
```

### Sync Service Status

**Via logs:**

```bash
tail -f ~/.claude/clc/logs/graph-sync.log
```

**Via API** (future enhancement):

```bash
curl http://localhost:8000/api/graph/sync/status
```

## Uninstalling

**To disable graph features:**

1. **Stop sync service:** `pkill -f graph_sync_service`
2. **Stop FalkorDB:** `docker stop clc-falkordb && docker rm clc-falkordb`
3. **Remove data volume:** `docker volume rm falkordb-data`

**System will continue working with SQLite alone.**

## Further Reading

- [FalkorDB Documentation](https://docs.falkordb.com/)
- [Auto-Claude Integration Spec](./implementation-plans/auto-claude-integration-spec.md)
- [Relationship Detection Algorithm](../memory/relationship_detector.py)
- [Graph Sync Implementation](../memory/graph_sync.py)

## Support

For issues or questions:

1. Check logs: `~/.claude/clc/logs/`
2. Verify FalkorDB: `docker logs clc-falkordb`
3. Test fallback: Stop FalkorDB and verify system still works
4. File an issue with relevant log snippets
