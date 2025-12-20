# Heuristic: Railway PR environments need DATABASE_URL override

**Domain:** infrastructure, railway, deployment
**Confidence:** 0.95
**Created:** 2025-12-19

## Pattern
When Railway shares production environment variables to PR environments, it also shares the production `DATABASE_URL`. This causes PR environment services to crash because they try to connect to the production database instead of the PR-specific database.

## Solution
For each PR environment, manually override `DATABASE_URL` to point to the PR environment's database instead of production.

## Trigger
- PR environment services crash on startup
- Services that worked before suddenly fail in PR preview
- Database connection errors in PR environment logs

## Context
Railway PR environments create their own database, but the variable sharing from production overwrites the PR database URL with the production one.
