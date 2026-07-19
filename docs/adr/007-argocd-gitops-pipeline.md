---
title: GitOps delivery model — Jenkins builds, ArgoCD deploys
date: 2026-07-19
status: accepted
---

## Context

The Phase 6 pipeline ran `helm upgrade --install` directly from Jenkins, coupling build and deploy. The database secret was injected at deploy time from a Jenkins credential. This model does not scale to multiple environments or services and has no continuous reconciliation.

## Decision

Split build and deploy responsibilities:

- **Jenkins** — builds the image, runs tests and security scans, pushes to ECR, then commits the new image tag to `deploy/helm/pacemoney/values.yaml` and pushes to `main`.
- **ArgoCD** — watches the `main` branch, detects the values.yaml change, and syncs the Helm release to the cluster automatically.

The database secret is no longer passed through Jenkins. It is fetched at runtime from AWS Secrets Manager by the External Secrets Operator running in the cluster (see ADR 011 in pacemoney-infra).

A Guard stage at the top of the Jenkinsfile checks the commit author. If it is `jenkins@kloudways.com` (i.e., an image-tag commit), the pipeline exits early with SUCCESS and a `[gitops]` label, preventing an infinite loop.

## Consequences

- The pipeline now has eight stages inside a `CI/CD` nested stage wrapper, guarded by the top-level Guard stage
- `values.yaml` image tag is updated on every successful build — the file acts as the deployment record
- `deploy/argocd/application.yaml` is the single source of truth for what ArgoCD deploys
- OWASP ZAP still runs at the end of the pipeline, but it may scan the previous image version if ArgoCD has not yet synced
