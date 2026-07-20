---
title: Serve frontend as FastAPI StaticFiles with no build step
date: 2026-07-20
status: accepted
---

## Context

The application needed a browser UI so users can interact with it without using the API directly.

## Decision

Mount FastAPI `StaticFiles` at `/static` and serve `app/static/index.html` at `GET /` via `FileResponse`. The frontend is vanilla HTML, CSS, and JavaScript with no framework or build step.

Assets are part of the same container image — no separate frontend server, CDN, or build pipeline is required.

## Consequences

- `aiofiles` must be installed (`StaticFiles` requires it at import time).
- Chrome's HTTPS-First mode (default since Chrome 116) blocks HTTP-only deployments. Users can bypass via `thisisunsafe` on the Chrome block page; the permanent fix is TLS on the load balancer.
- There is no asset bundling, minification, or cache-busting. For a lab project this is acceptable; a production deployment would need a CDN or versioned asset paths.
- The static directory must be present in the Docker image; it is included via `COPY app/ ./app/`.
