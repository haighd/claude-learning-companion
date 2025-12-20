-- Add Kanban task tracking table
-- This table stores tasks for the Kanban board, which can be automatically created
-- from failures, heuristics, and CEO inbox items

CREATE TABLE IF NOT EXISTS kanban_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'in_progress', 'review', 'done')),
    priority INTEGER DEFAULT 0,
    tags TEXT DEFAULT '[]',  -- JSON array
    linked_learnings TEXT DEFAULT '[]',  -- JSON array of learning IDs
    linked_heuristics TEXT DEFAULT '[]',  -- JSON array of heuristic IDs
    auto_created INTEGER DEFAULT 0,  -- Flag: was this auto-created?
    auto_source TEXT,  -- Source: 'failure', 'ceo_inbox', 'heuristic', 'manual'
    source_id TEXT,  -- ID of source record (learning_id, heuristic_id, or file path)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_kanban_status ON kanban_tasks(status);
CREATE INDEX IF NOT EXISTS idx_kanban_priority ON kanban_tasks(priority DESC);
CREATE INDEX IF NOT EXISTS idx_kanban_created ON kanban_tasks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_kanban_auto_source ON kanban_tasks(auto_source);
CREATE INDEX IF NOT EXISTS idx_kanban_source_id ON kanban_tasks(source_id);

-- Update schema version
INSERT OR REPLACE INTO schema_version (version, description)
VALUES (3, 'Added kanban_tasks table for task tracking');
