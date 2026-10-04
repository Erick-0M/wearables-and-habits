# Project context log

Running log of durable context accumulated across issues — decisions, data quirks, pitfalls, and anything future work should know. This file is auto-loaded into every Claude Code session via the `@reports/context.md` import in `CLAUDE.md`.

Append one section per issue below. Don't rewrite or delete prior entries. Keep each entry to a few bullets — this file's entire content is loaded into every session's context.

<!-- Example entry format:
## Issue #12 — <short title> (2026-09-11)
- Decision: ...
- Data quirk: ...
- Pitfall for future work: ...
-->

## Issue #1 — Planning (2026-10-03)
- Deliverable: `reports/project_plan_proposal_report.tex/.pdf` (plan proposal; numeric go/no-go thresholds, owners, deadlines still TBD).
- Key framing: Open e-commerce data observe purchases, not activity, so the outcome is running-related purchasing (proxy). Main threat is anticipation/selection (buying watch and shoes together).
- Design: staggered DiD with robust estimators (Callaway–Sant'Anna primary); structural extension (habit/learning/present-bias/BLP demand) only if reduced form clears a gate.
- Dataset facts in the plan (Amazon purchases + demographics) are from memory, unverified until the data audit.
- No `latexmk` locally; compile with `tectonic <file>.tex` from `reports/`.
- Planned phase issues: setup, data audit (go/no-go), design, analysis, robustness, reporting.
