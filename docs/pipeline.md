# CI/CD pipeline

The Jenkins pipeline is defined in `Jenkinsfile` at the repository root. It uses a Declarative Pipeline syntax with nine stages. The `ansiColor('xterm')` option is set globally so ANSI colour codes from tools like Gitleaks and pytest render correctly in the Jenkins console.

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
| `db-url` | Secret text | Helm Deploy |

## Stages

### 1. Gitleaks

Runs the Gitleaks container against the workspace to detect hardcoded secrets in the repository history.

```
docker run --rm -v ${WORKSPACE}:/repo ghcr.io/gitleaks/gitleaks:latest detect --source /repo --redact --verbose
```

**Fails on:** any detected secret in the commit history.  
**Passes on:** zero findings.

### 2. Unit Tests

Creates a Python virtual environment (venv), installs dependencies from `requirements.txt`, and runs the pytest test suite.

```
python3 -m venv .venv
.venv/bin/pip install --quiet -r requirements.txt
.venv/bin/pytest tests/ -v --tb=short
```

Tests use SQLite via the `DATABASE_URL` default. The `tests/conftest.py` fixture creates all tables before the session and drops them after.

**Fails on:** any pytest test failure.

### 3. SonarQube

Runs `sonar-scanner` against SonarCloud using the `sonar-token` credential.

```
sonar-scanner \
  -Dsonar.host.url=https://sonarcloud.io \
  -Dsonar.login=${SONAR_TOKEN}
```

Configuration is read from `sonar-project.properties`. SonarCloud Automatic Analysis must be disabled in the project settings for CI-based analysis to work.

**Fails on:** non-zero exit from sonar-scanner (authentication failure, configuration error).  
**Does not fail on:** code quality issues (SonarCloud quality gate failures are reported on the dashboard but do not block the build by default with this configuration).

### 4. Checkov

Installs Checkov and scans the Dockerfile only.

```
pip3 install --quiet --user checkov
~/.local/bin/checkov -d . --quiet --framework dockerfile
```

The `--framework dockerfile` flag restricts scanning to Dockerfile checks. Full IaC scanning is excluded to avoid false positives on kops-managed resources.

**Fails on:** any failed Dockerfile check. The Dockerfile must pass all Checkov Dockerfile checks, including CKV_DOCKER_2 (HEALTHCHECK required).

### 5. Docker Build

Sets `IMAGE_TAG` to the short git commit SHA, then builds and tags the image with both the SHA tag and `latest`.

```
docker build \
  -t ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG} \
  -t ${ECR_REGISTRY}/${ECR_REPO}:latest \
  .
```

**Fails on:** any Docker build error.

### 6. Trivy Scan

Scans the built image for HIGH and CRITICAL vulnerabilities, ignoring CVEs with no available fix.

```
trivy image \
  --exit-code 1 \
  --severity HIGH,CRITICAL \
  --ignore-unfixed \
  --no-progress \
  ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}
```

`--ignore-unfixed` suppresses CVEs where the upstream package has no fixed version available. This prevents the build from being blocked by base OS vulnerabilities outside the team's control.

**Fails on:** any HIGH or CRITICAL CVE with a fix available.

### 7. Push to ECR

Authenticates to ECR using the Jenkins IAM instance profile, then pushes both tags.

```
aws ecr get-login-password --region ${AWS_REGION} | \
  docker login --username AWS --password-stdin ${ECR_REGISTRY}
docker push ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}
docker push ${ECR_REGISTRY}/${ECR_REPO}:latest
```

Both the SHA-tagged image and `latest` are pushed on every successful build. The ECR lifecycle policy retains a maximum of 30 images and expires untagged images after 1 day.

**Fails on:** authentication failure, push error.

### 8. Helm Deploy

Exports the kops kubeconfig and runs `helm upgrade --install` with the new image tag and the database connection string from the `db-url` credential.

```
kops export kubecfg ${CLUSTER_NAME} \
  --state ${KOPS_STATE_STORE} --admin

helm upgrade --install pacemoney ./deploy/helm/pacemoney \
  --namespace pacemoney --create-namespace \
  --set image.repository=${ECR_REGISTRY}/${ECR_REPO} \
  --set image.tag=${IMAGE_TAG} \
  --set database.url=${DB_URL} \
  --wait --timeout 5m
```

The `--wait` flag causes Helm to poll until all pods are ready or the 5-minute timeout is reached. The `database.url` value is masked in the console log by Jenkins credentials binding.

When `database.url` is set, the Helm chart renders a Kubernetes Secret (`pacemoney-pacemoney-db`) containing `DATABASE_URL`, and the Deployment injects it as an environment variable.

**Fails on:** kops kubeconfig export failure (IAM permission error), Helm timeout (pods not ready within 5 minutes), Helm chart rendering error.

### 9. OWASP ZAP

Runs a ZAP (OWASP Zed Attack Proxy) baseline passive scan against the live application URL.

```
docker run --rm \
  -v ${WORKSPACE}:/zap/wrk:rw \
  ghcr.io/zaproxy/zaproxy:stable \
  zap-baseline.py -t ${APP_URL} -r zap-report.html || true
```

The workspace is mounted at `/zap/wrk` so ZAP can write the HTML report. The `|| true` ensures the stage does not fail the build on ZAP warnings, only on ZAP errors (which are also suppressed by `|| true`). ZAP findings are visible in the console log.

**Never fails the build** (due to `|| true`). This is intentional: ZAP baseline warnings on a development application would be noise rather than actionable signal.

## Post actions

On every run (success or failure):

```
docker rmi ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG} || true
docker rmi ${ECR_REGISTRY}/${ECR_REPO}:latest || true
cleanWs()
```

The built images are removed from the Jenkins host to prevent disk exhaustion. `cleanWs()` deletes the workspace.

On success: a message is printed with the deployed image tag and cluster name.  
On failure: a message directs the operator to the stage logs.

## Stage execution order and skip behaviour

Stages execute sequentially. If any stage fails (exits non-zero), all subsequent stages except post actions are skipped. The exception is OWASP ZAP, which uses `|| true` and therefore cannot cause downstream skips even if ZAP exits non-zero.
