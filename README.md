# pacemoney-app

Application code, container image, Helm chart, and Jenkins pipeline for the Pace Money portfolio project. The application is a FastAPI expense tracker backed by PostgreSQL in production and SQLite in local development and tests.

## Repository structure

```
pacemoney-app/
├── app/
│   ├── main.py         # FastAPI application, routes, lifespan
│   ├── database.py     # SQLAlchemy engine and session factory
│   └── models.py       # ORM models
├── tests/
│   ├── conftest.py     # Session-scoped fixture: creates DB tables before tests
│   └── test_health.py  # Tests for /health, /metrics, /transactions
├── deploy/
│   └── helm/
│       └── pacemoney/  # Helm chart
│           ├── Chart.yaml
│           ├── values.yaml
│           └── templates/
│               ├── deployment.yaml
│               ├── service.yaml
│               ├── secret.yaml      # Only rendered when database.url is set
│               └── servicemonitor.yaml
├── Dockerfile
├── Jenkinsfile
├── requirements.txt        # All dependencies (dev + prod)
├── requirements-prod.txt   # Production dependencies only (references requirements.txt)
└── sonar-project.properties
```

## Running locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The application starts on `http://localhost:8000`. Without `DATABASE_URL` set, it uses SQLite (`./pacemoney.db`).

## Running tests

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v
```

Tests use SQLite via the `DATABASE_URL` default. The `conftest.py` fixture creates all tables before the test session and drops them after.

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | No | `sqlite:///./pacemoney.db` | SQLAlchemy connection string. In Kubernetes, injected from a Secret created by Helm. |

In production the connection string is:

```
postgresql+psycopg2://<username>:<password>@<rds-endpoint>:5432/<dbname>
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Returns `{"status": "ok", "app": "pacemoney"}` |
| GET | `/metrics` | Prometheus metrics |
| GET | `/transactions` | List all transactions |
| POST | `/transactions` | Create a transaction |
| DELETE | `/transactions/{id}` | Delete a transaction |

## Helm chart

The Helm chart is in `deploy/helm/pacemoney/`. Key values:

| Value | Default | Description |
|-------|---------|-------------|
| `image.repository` | ECR repository URL | Container image repository |
| `image.tag` | `latest` | Image tag (overridden by pipeline with git short SHA) |
| `replicaCount` | `2` | Number of pod replicas |
| `database.url` | `""` | PostgreSQL connection string. When set, a Kubernetes Secret is created and `DATABASE_URL` is injected into the container. |
| `service.type` | `LoadBalancer` | Kubernetes Service type |
| `service.port` | `80` | Service port |
| `app.port` | `8000` | Container port |

## Jenkins pipeline

See `docs/pipeline.md` for a full description of all pipeline stages.

Required Jenkins credentials:

| Credential ID | Type | Description |
|--------------|------|-------------|
| `sonar-token` | Secret text | SonarCloud analysis token |
| `db-url` | Secret text | Full PostgreSQL connection string for RDS |
