# template

A template repository for research projects that combine a data pipeline (Python/R/etc.), a LaTeX paper, and per-issue LaTeX reports, developed with [Claude Code](https://claude.com/claude-code).

## Repository structure

```
code/
  scripts/           # all code (.py, .R, .do, .ipynb, .sh, .sql, .jl, .m, .cpp, .c, .stan)
  analysis/outputs/  # committed deliverable figures/tables referenced by paper/ or reports/
  analysis/input/    # gitignored
  analysis/interm/   # gitignored
  build/             # gitignored working directory (input/interm/outputs)
  gcp-shared-config/ # gitignored credentials mount
  Dockerfile, docker-compose.yaml, requirements.txt
paper/               # the LaTeX paper (main.tex \input-ing introduction/, literature/, theory/, data/, methods/, conclusion/)
reports/             # one report.tex + report.pdf per closed issue, plus the running context.md log
references/          # read-only guidance carried over from prior projects — never edit
.claude/             # Claude Code settings, hooks, and permissions for this repo
```

## Running the code

Everything runs inside the project container:

```
cd code
docker compose up --build
```

This starts a Jupyter environment (`jupyter/datascience-notebook` base image) with `code/scripts`, `code/build`, and `code/analysis` mounted in. Add new Python/R/etc. dependencies to `code/requirements.txt` and `code/Dockerfile`.

## The paper

`paper/main.tex` assembles the paper from per-section files (`introduction/`, `literature/`, `theory/`, `data/`, `methods/`, `conclusion/`) and `paper/references.bib`. Compile with `latexmk -pdf paper/main.tex`. Figures/tables the paper references must live in `code/analysis/outputs/`, not directly in `paper/`.

## Working with Claude Code

This repo is meant to be driven through Claude Code, with the full conventions documented in [CLAUDE.md](CLAUDE.md). The short version:

1. Every task starts as a GitHub issue, then a linked branch.
2. Work is delivered as `reports/<topic>_<scope>_report.tex` + compiled `.pdf`.
3. Before closing the issue: push the branch, post a summary comment, and append an entry to `reports/context.md` (a running log of durable project context, auto-loaded into every Claude Code session).
4. Closing the issue (`gh issue close`) ends the Claude Code session — a hook enforces this, so it's the last step, not something to do mid-task.
5. **Merging the branch/PR into `main` is done by the user**, not by Claude.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
