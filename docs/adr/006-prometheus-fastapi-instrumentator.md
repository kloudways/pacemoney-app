---
title: Replace manual prometheus_client with prometheus-fastapi-instrumentator
date: 2026-07-19
status: accepted
---

## Context

The original `/metrics` implementation used `prometheus_client` directly with a manually incremented `Counter` wired to two routes. This left `/health` and `DELETE /transactions` untracked and provided only a counter, not the histograms (request duration, status codes) that Grafana dashboards need.

## Decision

Replace the manual approach with `prometheus-fastapi-instrumentator==8.0.2`. A single line instruments all routes automatically:

```python
Instrumentator().instrument(app).expose(app)
```

This provides `http_request_duration_seconds` histograms and `http_requests_total` counters for every route, labelled by method, handler, and status code.

## Consequences

- The custom metric `pacemoney_requests_total` no longer exists; the test asserting it was updated to check `http_request_duration_seconds`
- All routes are instrumented automatically — no per-route boilerplate
- The `/metrics` endpoint is registered by the instrumentator; the manual endpoint was removed
