# ADR 003: Checkov scoped to Dockerfile framework only

**Date:** 2026-07  
**Status:** Accepted

## Context

Checkov supports scanning multiple frameworks: Dockerfile, Terraform, Kubernetes manifests, Helm charts, and others. Running `checkov -d .` with no framework filter scans everything in the repository.

The repository contains a Helm chart with Kubernetes manifests and a Jenkinsfile. Scanning these with Checkov would produce findings related to the kops-managed infrastructure (for example, missing Pod Security Admission labels, network policies) that are not under the application team's control and would not be actionable.

## Decision

Run Checkov with `--framework dockerfile` to restrict scanning to the Dockerfile only.

```bash
checkov -d . --quiet --framework dockerfile
```

## Consequences

- The Dockerfile must pass all Checkov Dockerfile checks (currently 43 passing checks, 0 failing).
- Helm chart and Kubernetes manifest security scanning is not performed in this pipeline. This is a known gap, acceptable for a portfolio project.
- If Helm chart scanning is added in the future, a Checkov configuration file (`.checkov.yaml`) should be used to suppress known false positives rather than widening the scope globally.
