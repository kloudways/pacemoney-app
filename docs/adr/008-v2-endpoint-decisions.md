---
title: Phase 8 v2 — endpoint additions and route ordering
date: 2026-07-19
status: accepted
---

## Context

Phase 8 adds three capabilities to the API: fetching a single transaction by ID, a spending summary by category, and a version field in the health check. Two non-obvious decisions arose during implementation.

## Decision 1 — Route ordering: summary before `{tx_id}`

`GET /transactions/summary` must be registered before `GET /transactions/{tx_id}`. FastAPI matches routes in definition order. If the path-parameter route were first, a request to `/transactions/summary` would be captured with `tx_id="summary"`, which fails Pydantic integer validation and returns a 422 instead of the summary response.

## Decision 2 — Version sourced from `app.version`

The `/health` endpoint returns `app.version` rather than a hardcoded string or an environment variable. The FastAPI constructor is the single declaration point (`version="2.0.0"`); reading it back avoids a second place to update on every release. Bumping the version in the constructor is visible in a diff and sufficient.

## Decision 3 — Test isolation via unique category names and per-test cleanup

The test suite uses a session-scoped SQLite database. Tests run sequentially and accumulate rows. Summary tests that assert absolute totals will fail unless the database is in a known state. Rather than change the fixture scope (which would slow down the suite), summary tests use category names that no other test uses (`housing_v2`, `food_v2`) and delete their own rows after asserting. This keeps tests fast and independent without requiring test ordering or database truncation between each test.
