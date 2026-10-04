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

## Issue #3 — Setup, data download, packages (2026-10-04)
- Data: Open e-commerce 1.0 (CC0) in `code/build/input/public/open_ecommerce/` (gitignored); re-fetch with `code/scripts/download_open_ecommerce.py`. Dataverse needs a User-Agent; `survey.csv` must be fetched with `?format=original` (listed md5 is the original's).
- Facts: 1.85M purchase rows, 5,027 users, 2018-01 to 2024-08; columns are date, price, qty, state, title, ASIN, category, respondent ID. Survey has demographics but NO running/exercise items, so the proxy can't be validated in-data.
- Crude title-keyword flag: ~2,000 ever-treated, ~1,100 with ≥12m pre and post; it includes accessories (watch bands) — use the `Category` field (e.g. WEARABLE_COMPUTER, BIOMETRIC_MONITOR, SHOES) in the audit.
- Packages in the existing container: R `did`, `fixest`, `HonestDiD`, `didimputation`, `bacondecomp`; Python `pyfixest`. Pitfalls: HonestDiD is GitHub-only, Rglpk needs conda `glpk`, CVXR pinned to 1.0-15 (no Rust), R `arrow` unavailable (use pyarrow). Run estimation in R, data prep in Python.

## Issue #5 — Data audit, variables, balance, data quality (2026-10-04)
- Deliverable: `reports/data_audit_open_ecommerce_report.tex/.pdf`; scripts `code/scripts/data_audit_open_ecommerce.py`, `data_quality_checks.py`. Intermediates (gitignored, `code/build/interm/`): `panel_user_month.pkl`, `panel_user_quarter.csv`, `purchases_flagged.pkl`.
- Usable window is 2018-01 to 2023-03; users are observed from first to last purchase and nearly all windows end by early 2023 (restrict calendar series to months with ≥1,000 active users).
- Treatment = first purchase in `WEARABLE_COMPUTER`/`BIOMETRIC_MONITOR`, kids' trackers excluded (940 users, 570 with ≥12m pre and post); "clean" = also price ≥$40, qty 1, not an accessory (723; 447). Outcomes: running-shoe, running-related (keyword, noisy: ~21% of flagged rows are shoes), fitness gear, supplements, medication (`MEDICATION`+`OTC_MEDICATION`, human OTC only).
- Pitfalls: Category/Title missing for 10% of rows in 2018 vs 1% in 2022, which undercounts flagged outcomes early and inflates trends (use shares or year effects); 37% of users have a >180-day purchase gap, so zero months are weak signals; descriptive event-time means show a spike at t=0 (device purchase) and rising pre-adoption purchasing.
- Balance fails (all joint F p<0.01): adopters have higher income, more often white, larger households, longer windows, higher overall purchasing and ~2x running purchases. Check N after every merge (a "1 (just me!)" household-size answer was silently dropped once).
- Compose `container_name: research-container` collides with another project's container; run with `docker compose run --rm --no-deps opt ...` from `code/`. R `fixest`/`did` load in this repo's image. No event-study estimates yet; that is the next issue.

## Issue #7 — Design: staggered DiD, placebos, shoe bundling, lifestyle controls (2026-10-04)
- Deliverable: `reports/design_event_study_report.tex/.pdf`; scripts `code/scripts/prep_design_panel.py`, `prep_design_covariates.py`, `design_did.R`, `design_did_balanced.R`, `design_did_lifestyle.R`, `design_did_figs.py`. Panel is user-quarter (`build/interm/design_panel_q.csv`, gitignored); R reads CSV; event studies use `base_period="universal"` so the reference is e=-1.
- Main result: no detectable post-adoption increase in running purchases (post ATT q1-8: running shoe -0.016 (0.009), running-related -0.033 (0.016)), but strong pre-trends in nearly all outcomes INCLUDING placebos (pet, books, grocery...): adopters ramp up purchasing before the device. The unconditional DiD is not credible.
- Pre-trend survives a balanced panel (users observed 2018Q1-2022Q4) and doubly-robust conditioning on baseline lifestyle (first-4-quarter purchase-mix PCs + survey demographics; overlap fine). So the confounder is time-varying and pre-adoption (life events, emerging fitness routine), not a fixed baseline trait or attrition. Next: time-varying purchasing-intensity control/shares, not-yet-treated controls, HonestDiD.
- Bundling is thin: only 30 of 570 adopters (24 of 447 clean) buy running shoes within +-1 month of the device; underpowered, only fitness gear differs (-0.144, SE 0.072). Running-shoe-as-treatment: no later wearable purchase, +0.029 (0.014) non-shoe running-related.
- Pitfalls: `did` joint pre-test Wald is 0.000/n/a (singular), rely on plots; `\text` needs amsmath (not loaded), escape `#` in table labels; conditional DR run takes ~10+ min (run in background).
