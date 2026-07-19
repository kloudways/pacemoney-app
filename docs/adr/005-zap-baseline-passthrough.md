# ADR 005: OWASP ZAP stage does not fail the build

**Date:** 2026-07  
**Status:** Accepted

## Context

The OWASP ZAP baseline scan performs passive scanning against the live application. Passive scanning does not send attack payloads; it observes HTTP responses and flags potential issues such as missing security headers and cacheable content.

A ZAP baseline scan on a minimal API application without a web frontend will produce warnings for missing headers (Content Security Policy, X-Frame-Options) that would require additional middleware to address. These warnings are informational for a portfolio project.

ZAP exits with a non-zero code when warnings are found. If the stage propagates this exit code, any ZAP warning would fail the entire pipeline.

## Decision

Append `|| true` to the ZAP docker run command so the stage always passes regardless of ZAP's exit code.

```bash
docker run --rm \
  -v ${WORKSPACE}:/zap/wrk:rw \
  ghcr.io/zaproxy/zaproxy:stable \
  zap-baseline.py -t ${APP_URL} -r zap-report.html || true
```

## Consequences

- ZAP findings are visible in the Jenkins console log but do not block deployment.
- A genuine vulnerability found by ZAP would be visible to anyone reviewing the build log but would not prevent the release.
- If the pipeline is extended for production use, the `|| true` should be replaced with a ZAP configuration file (`-c config_file`) that sets specific rules to FAIL and others to WARN, and the `|| true` removed.
- The HTML report (`zap-report.html`) is written to the workspace but is not currently archived as a Jenkins artifact. The scan output is available in the console log only.
