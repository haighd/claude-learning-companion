# Changelog

All notable changes to claude-learning-companion (formerly Emergent Learning Framework) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-16

### Fork Independence Release

This release marks the transition from upstream contribution to an independent project.

### Added
- **Comprehensive Update System** (`update.sh` / `update.ps1`)
  - Hybrid git/standalone support
  - Interactive conflict resolution (Update/Keep/Diff/Backup options)
  - Customization detection via SHA256 file hashes
  - Automatic backup and rollback on failure
  - Database migration integration
  - Version checking against GitHub releases
- **Database Migrations** (`scripts/migrate_db.py`)
  - Sequential SQL migration runner
  - Schema version tracking
- **Customization Detection** (`.stock-hashes`)
  - SHA256 hashes of stock files
  - Warns before overwriting customized files
- Async Query Engine (from upstream 0.2.0)
- ELF MCP Server (from upstream 0.2.0)
- Step-file Workflows (from upstream 0.2.0)

### Changed
- Project renamed to `claude-learning-companion`
- VERSION set to 1.0.0 for fresh start as independent project

### Inherited from Upstream
- Dashboard UI with cosmic theme
- Golden rules and heuristics system
- CEO escalation workflow
- Agent personas (Architect, Creative, Researcher, Skeptic)
- Learning pipeline automation
- File operations tracking

---

## Pre-Fork History (Upstream)

### [0.2.0] - 2025-12-16 (Upstream)
- Async Query Engine migration
- ELF MCP Server for claude-flow
- Step-file Workflows
- Party Definitions
- Simple update system

### [0.1.2] - 2025-12-14 (Upstream)
- Dashboard UI overhaul
- Learning pipeline automation

### [0.1.1] - 2025-12-13 (Upstream)
- Initial dashboard application
- Golden rules system

### [0.1.0] - 2025-12-12 (Upstream)
- Initial release

---

## Versioning Policy

- **Major (X.0.0)**: Breaking changes to database schema or configuration
- **Minor (0.X.0)**: New features, backward-compatible
- **Patch (0.0.X)**: Bug fixes, documentation updates
