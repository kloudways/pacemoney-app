## Documentation cadence
After completing any phase (2 through 8), update documentation before moving to the next phase. This is a standing rule, not something the user needs to ask for.
Always update after every phase:
1. docs/issues-log.md — append any new issues encountered, with columns Issue | Phase | Symptom | Root cause | Fix | Prevention. If the file does not exist yet, create it with headers.
2. docs/adr/ — one new markdown file per non-obvious decision made during the phase. Naming pattern: NNNN-short-decision-title.md, incrementing NNNN.
Update when the phase adds new content:
3. README.md at the repository root — reflect the current state accurately.
4. docs/architecture.md (pacemoney-infra) or docs/pipeline.md (pacemoney-app) — reflect any structural or operational change.
5. docs/runbook.md (pacemoney-infra) — add any new operational commands or troubleshooting steps introduced by the phase.
Commit on a branch named docs/phase-N where N is the phase number just completed. Do not push. Report back to the user with a summary of what was updated and in which files, so the user can review and push manually.
Do not invent behaviour that is not in the code. If a decision or change is not visible in the code or commit history for the phase just completed, do not fabricate it.
