---
title: Ship Grafana dashboard as a Helm ConfigMap with sidecar discovery
date: 2026-07-20
status: accepted
---

## Context

The Grafana dashboard built in Phase 6 existed only inside Grafana's database. Every cluster rebuild destroyed it, requiring a manual re-import.

## Decision

Add `deploy/helm/pacemoney/templates/grafana-dashboard.yaml` — a ConfigMap containing the dashboard JSON, labelled `grafana_dashboard: "1"`. The `kube-prometheus-stack` sidecar discovers ConfigMaps with this label across all namespaces and loads them into Grafana automatically.

The dashboard is version-controlled alongside the application code and deployed as part of the app Helm release.

## Consequences

- `kube-prometheus-stack` must be installed before the first app Helm release so the sidecar is running when the ConfigMap is created.
- The dashboard uses `job="pacemoney-pacemoney"` as the Prometheus selector, which matches the label set by the ServiceMonitor. If the release name or namespace changes, the selector must be updated.
- Dashboard changes go through the normal git → Jenkins → ArgoCD flow.
