# Profile README metrics builder

Refreshes the `<!--START_SECTION:metrics-->` … `<!--END_SECTION:metrics-->` block in the repo root `README.md` with GitHub stats.

## Prerequisites

- Python 3.12+
- GitHub personal access token with `repo` and `read:user` (`GH_TOKEN`)

## Local run

From the repository root (`piyushmishra318/`):

```bash
export GH_TOKEN="your-github-pat"

python -m pip install -r scripts/requirements.txt
python scripts/build_readme.py
```

On Windows (PowerShell):

```powershell
$env:GH_TOKEN = "your-github-pat"
python -m pip install -r scripts/requirements.txt
python scripts/build_readme.py
```

The script updates `README.md` in place. Review the diff before committing.

### Metrics sections (in order)

1. **GitHub Snapshot** — yearly contributions, 7/30-day activity, streaks, repo count, storage
2. **Collaboration** — open/merged PRs, issues opened, reviews given
3. **Most Active Repos** — top 5 repos by commit count
4. **When I Code** — time-of-day, weekday, weekend split, busiest month
5. **Mostly X Repos** — primary language breakdown
6. **AI vs Manual** — heuristic split from commit messages (Copilot, Cursor, etc.)

## CI

`.github/workflows/update-readme.yml` runs daily at 18:30 UTC (00:00 IST) and on `workflow_dispatch`. Secret: `GH_TOKEN`.

## Profile view counter

Self-hosted badge stored in `assets/profile-views.svg` (no komarev dependency).

- Script: `scripts/update_profile_views.py`
- Workflow: copy `scripts/profile-views.workflow.yml` → `.github/workflows/profile-views.yml` on GitHub (Actions → New workflow)
- Data: `assets/profile-views.json` accumulates GitHub traffic insights for this repo
- README embed: `raw.githubusercontent.com/.../assets/profile-views.svg`

To seed a starting count (e.g. from an old komarev total), set `"base"` in `assets/profile-views.json`.

## Out of scope (v1)

- Lines-of-code badge
- Quarterly LOC timeline / `bar_graph.png`
- Commit path filtering via `EXCLUDED_COMMIT_PATH_PATTERNS` (defined in `profile_config.py` for later use)
