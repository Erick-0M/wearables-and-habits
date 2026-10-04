## Project context
@reports/context.md
- The import above pulls the running log of durable project context (decisions, data quirks, findings accumulated across issues) into every session automatically. Read it before starting new work.
- Keep entries terse (a few bullets per issue) — this file is loaded into every session's context, so bloat here has an ongoing cost.
## Exploratory analysis principle
- Treat all analysis work as exploratory, never final. Prefer the simplest, most direct approach that answers the question; don't over-engineer, over-validate, or overthink.
- Don't spend extra tokens or compute on polish, exhaustive robustness checks, or speculative extensions unless the user asks; note follow-ups briefly instead of doing them.
- This governs analytical effort only — the workflow rules below (git, LaTeX, issue, pipeline, repo structure) still apply as written.
## Git workflow
- After committing, ALWAYS `git push -u origin <branch>` and then verify with `git ls-remote --heads origin <branch>` (or `gh browse`). Never report work as "committed" until the branch is visible on GitHub.
- Before committing, run `git status --porcelain` and confirm the file list matches intent; avoid bare `git add -A` (it has silently produced incomplete commits here).
## LaTeX reports
- Reports and deliverables are LaTeX (.tex) compiled to PDF.
- After every .tex edit, recompile (`latexmk -pdf <file>.tex`) and confirm zero errors; check the log for overfull hboxes on tables and fix them before reporting done.
- Only use macros already defined in the preamble (e.g. do not invent \E, \degree); grep the preamble first.
- Name reports descriptively: `<topic>_<scope>_report.tex`.
## GitHub issue workflow
- Standard flow for a new task: create the GitHub issue first, capture the real issue number from `gh issue create` output (never use placeholder numbers in cross-references), create and push a linked branch, then work.
- Merging the branch/PR into `main` is done by the user, not by Claude — never run `gh pr merge` or merge a branch unprompted.
- Every issue's deliverable is a `reports/<topic>_<scope>_report.tex` + compiled `.pdf` (see LaTeX reports rules above).
- When embedding images in issue/PR comments, this repo is PRIVATE — use `raw.githubusercontent.com` links, verify that they render.
- Close the loop by posting a summary comment on the issue when the branch is pushed.
- `reports/context.md` is updated ONLY when an issue is actually closed (`gh issue close`), never mid-work or at branch-push time: append a dated, issue-numbered section summarizing what future issues/the project should know (decisions made, data quirks found, pitfalls) — don't rewrite prior entries.
- A hook (`.claude/hooks/close-issue-end-session.sh`) ends the Claude session immediately after a successful `gh issue close`. Nothing runs after that point, so finish the push, the PR/issue summary comment, and the `reports/context.md` update BEFORE closing the issue — closing it is the last action of the session.
## Data pipelines
- Run everything in the existing project container (`code/` container) with pickle outputs. If a task genuinely needs a different/additional container, raise it with the user AND document it as a comment in `code/docker-compose.yaml` (or the new compose file, if the container lives elsewhere) explaining what it's for and why the existing container couldn't serve.
- Any bulk download must include retry/backoff and resume logic — the source endpoints reset connections on large multi-file pulls.
## Repository structure
- All code (`.py`, `.R`, `.do`, `.ipynb`, `.sh`, `.sql`, `.jl`, `.m`, `.cpp`, `.c`, `.stan`) lives under `code/scripts/`. Never create scripts loose in `code/`, `paper/`, or `reports/`.
- Every figure, table, or `\input{}`-able table/figure `.tex` fragment referenced by a report or paper (`.png`, `.pdf`, `.jpg`, `.svg`, `.csv`, `.tex` fragments) must be produced into `code/analysis/outputs/` and referenced from there — never commit a figure or table file directly inside `paper/` or `reports/`.
- `code/analysis/outputs/` is committed to git; `code/build/outputs/` is gitignored (see `.gitignore`). Deliverable figures/tables belong in `code/analysis/outputs/`, not `code/build/outputs/`.
- Files under `references/` are read-only guidance from past projects/prior efforts done outside this workflow — never edit, delete, or move them. If something there looks outdated or wrong, flag it to the user instead of changing it.
