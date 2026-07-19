# ADR 001: DATABASE_URL environment variable with SQLite fallback

**Date:** 2026-07  
**Status:** Accepted

## Context

The application needs to connect to a PostgreSQL database in production but must also run in local development and CI tests without requiring a live database.

## Decision

Read the database connection string from the `DATABASE_URL` environment variable. Default to `sqlite:///./pacemoney.db` when the variable is not set.

```python
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pacemoney.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
```

In Kubernetes, `DATABASE_URL` is injected from a Secret created by the Helm chart. The Secret is only rendered when `database.url` is set in Helm values:

```yaml
{{- if .Values.database.url }}
apiVersion: v1
kind: Secret
...
{{- end }}
```

## Consequences

- Tests run against SQLite without any external dependency.
- The same Docker image runs in any environment: the database backend is determined entirely by the environment variable.
- The Helm chart will not create a Secret (or inject `DATABASE_URL`) if `--set database.url` is omitted. In that case the container falls back to SQLite, which will fail if the SQLite file path is not writable. This is a misconfiguration guard, not a feature.
- The `postgresql+psycopg2` driver is installed in the production image (`requirements-prod.txt`). Tests do not exercise the PostgreSQL code path.
