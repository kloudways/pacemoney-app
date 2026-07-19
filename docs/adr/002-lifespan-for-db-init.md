# ADR 002: Database table creation in FastAPI lifespan event

**Date:** 2026-07  
**Status:** Accepted

## Context

`Base.metadata.create_all(bind=engine)` must run once at application startup to ensure the database schema exists.

The original implementation called `create_all` at module level, before the FastAPI application object was instantiated:

```python
from .database import engine, Base
Base.metadata.create_all(bind=engine)  # module level
app = FastAPI(...)
```

This caused a critical production failure. When the database was unreachable (due to a security group misconfiguration), the Python process blocked on the TCP connection attempt before uvicorn had a chance to bind to port 8000. The liveness probe (which checks `http://:8000/health`) never received a response, so Kubernetes killed the container with SIGKILL (exit code 137) after three probe failures. Because the process was blocked before writing anything to stdout or stderr, the logs were completely empty, making diagnosis very difficult.

## Decision

Move `create_all` to a FastAPI lifespan event:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="Pace Money", version="1.0.0", lifespan=lifespan)
```

## Consequences

- uvicorn binds to port 8000 before the lifespan event runs, so the health endpoint becomes reachable earlier in the startup sequence.
- If `create_all` fails (for example, due to a database connection error), the error is logged by uvicorn before the container is killed, making diagnosis much easier.
- The liveness probe will still fail if the lifespan event hangs indefinitely, but the root cause will be visible in the logs.
- The test suite uses `TestClient(app)` at module level without a context manager, so the lifespan does not run during tests. A `tests/conftest.py` session fixture calls `create_all` directly to compensate.
