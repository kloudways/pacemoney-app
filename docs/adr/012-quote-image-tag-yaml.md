---
title: Always quote image tags in values.yaml to prevent YAML integer parsing
date: 2026-07-20
status: accepted
---

## Context

The Jenkinsfile used `sed` to write the image tag into `values.yaml`:

```bash
sed -i "s|^  tag:.*|  tag: ${env.IMAGE_TAG}|" deploy/helm/pacemoney/values.yaml
```

When the git SHA was `4952336` (all decimal digits), YAML parsed it as the integer `4952336`. Helm rendered it in scientific notation (`4.952336e+06`), which is not a valid Docker image reference. The pod failed with `InvalidImageName`.

Previous tags (`8cc89e5`) were hexadecimal strings and were never parsed as numbers, so this did not surface earlier.

## Decision

Always write the image tag as a quoted YAML string. The Jenkinsfile `sed` now writes:

```bash
sed -i "s|^  tag:.*|  tag: \"${env.IMAGE_TAG}\"|" deploy/helm/pacemoney/values.yaml
```

The `values.yaml` default value is also quoted: `tag: "latest"`.

## Consequences

- The `sed` pattern must include escaped quotes; forgetting them reintroduces the bug.
- Any tooling that reads `values.yaml` and strips quotes must be tested with all-digit SHAs.
