# ADR 004: Trivy --ignore-unfixed flag

**Date:** 2026-07  
**Status:** Accepted

## Context

The `python:3.12-slim` base image is built on Debian. At the time this pipeline was built, Trivy reported 22 HIGH or CRITICAL CVEs in the Debian packages. All 22 had status "affected" with no fixed version available upstream.

Without `--ignore-unfixed`, Trivy exits with code 1 and blocks the build. The team has no mechanism to fix these CVEs: they are in Debian's package repositories, and the only options would be to wait for a Debian fix or switch base images entirely (which would introduce different CVEs).

## Decision

Add `--ignore-unfixed` to the Trivy invocation:

```bash
trivy image \
  --exit-code 1 \
  --severity HIGH,CRITICAL \
  --ignore-unfixed \
  --no-progress \
  ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}
```

## Consequences

- CVEs with no available fix are suppressed and do not block the build.
- CVEs that do have a fix available will still cause the build to fail, which is the intended behaviour.
- If a fix becomes available for a previously suppressed CVE, the next build will surface it automatically.
- The decision to use `--ignore-unfixed` should be reviewed periodically. If the number of fixable CVEs grows, upgrading the base image (for example, from `python:3.12-slim` to a newer patch release or a different base) is the correct remediation.
