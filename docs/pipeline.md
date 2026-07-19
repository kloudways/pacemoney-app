# CI/CD pipeline

The Jenkins pipeline is defined in `Jenkinsfile` at the repository root. It uses a Declarative Pipeline syntax with a Guard stage and a nested `CI/CD` stage containing eight stages. The `ansiColor('xterm')` option is set globally so ANSI colour codes from tools like Gitleaks and pytest render correctly in the Jenkins console.

## Delivery model

Jenkins is responsible for building, testing, and publishing. ArgoCD is responsible for deployment.

After a successful image push to ECR, Jenkins commits the new image tag to `deploy/helm/pacemoney/values.yaml` and pushes to `main`. ArgoCD detects the change (within three minutes) and syncs the Helm release to the cluster. Jenkins never runs `helm upgrade` directly.

The database secret is not passed through Jenkins. The External Secrets Operator reads it from AWS Secrets Manager and creates a Kubernetes Secret in the `pacemoney` namespace.

## Environment variables

| Variable | Value | Description |
|----------|-------|-------------|
| `ECR_REGISTRY` | `684779207098.dkr.ecr.eu-west-2.amazonaws.com` | ECR registry hostname |
| `ECR_REPO` | `pacemoney` | ECR repository name |
| `AWS_REGION` | `eu-west-2` | AWS region |
| `KOPS_STATE_STORE` | `s3://pacemoney-kops-state` | kops state bucket |
| `CLUSTER_NAME` | `pacemoney.k8s.local` | kops cluster name |
| `APP_URL` | `http://pacemoney.kloudways.com` | Application URL for OWASP ZAP |

`IMAGE_TAG` is set at runtime using `git rev-parse --short HEAD` during the Docker Build stage.

## Required Jenkins credentials

| Credential ID | Type | Used in stage |
|--------------|------|--------------|
| `sonar-token` | Secret text | SonarQube |
| `github-token` | Username+Password (GitHub PAT with `repo` scope) | Update Image Tag |

## Stages

### Guard

Checks the author email of the last commit. If it is `jenkins@kloudways.com` (an image-tag commit made by the Update Image Tag stage), the build is labelled `[gitops]` and all subsequent stages are skipped. The build result is `SUCCESS`. This prevents an infinite webhook loop.

### CI/CD (nested stages — skipped when Guard sets `[gitops]`)

#### 1. Gitleaks

Runs the Gitleaks container against the workspace to detect hardcoded secrets in the repository history.

```
docker run --rm -v ${WORKSPACE}:/repo ghcr.io/gitleaks/gitleaks:latest detect --source /repo --redact --verbose
```

**Fails on:** any detected secret in the commit history.

#### 2. Unit Tests

Creates a Python virtual environment, installs dependencies from `requirements.txt`, and runs the pytest test suite.

```
python3 -m venv .venv
.venv/bin/pip install --quiet -r requirements.txt
.venv/bin/pytest tests/ -v --tb=short
```

Tests use SQLite via the `DATABASE_URL` default. The `tests/conftest.py` fixture drops and recreates all tables before the session.

**Fails on:** any pytest test failure.

#### 3. SonarQube

Runs `sonar-scanner` against SonarCloud using the `sonar-token` credential. Configuration is read from `sonar-project.properties`.

**Fails on:** non-zero exit from sonar-scanner.

#### 4. Checkov

Installs Checkov and scans the Dockerfile only (`--framework dockerfile`).

**Fails on:** any failed Dockerfile check.

#### 5. Docker Build

Sets `IMAGE_TAG` to the short git commit SHA, then builds and tags the image with both the SHA tag and `latest`.

**Fails on:** any Docker build error.

#### 6. Trivy Scan

Scans the built image for HIGH and CRITICAL vulnerabilities. `--ignore-unfixed` suppresses CVEs with no upstream fix.

**Fails on:** any HIGH or CRITICAL CVE with a fix available.

#### 7. Push to ECR

Authenticates to ECR via the Jenkins IAM instance profile and pushes both the SHA-tagged image and `latest`.

**Fails on:** authentication failure, push error.

#### 8. Update Image Tag

Updates `deploy/helm/pacemoney/values.yaml` with the new `IMAGE_TAG`, commits as `jenkins@kloudways.com`, and pushes to `main` using the `github-token` credential. ArgoCD detects this change and deploys the new image.

**Fails on:** git commit or push error (e.g., invalid `github-token` credential).

#### 9. OWASP ZAP

Runs a ZAP baseline passive scan against `APP_URL`. The workspace is mounted at `/zap/wrk` so ZAP can write the HTML report.

**Never fails the build** (due to `|| true`).

## Post actions

On every run (success or failure):

```
docker rmi ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG} || true
docker rmi ${ECR_REGISTRY}/${ECR_REPO}:latest || true
cleanWs()
```

On success: a message is printed confirming the image was pushed and ArgoCD will sync.
On failure: a message directs the operator to the stage logs.

## Stage execution order and skip behaviour

The Guard stage runs unconditionally. If it sets `[gitops]`, the entire `CI/CD` stage block is skipped. Within `CI/CD`, stages execute sequentially — a failure in any stage skips all subsequent stages except post actions. OWASP ZAP cannot cause downstream skips due to `|| true`.
