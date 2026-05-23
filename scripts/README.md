# Profile README metrics builder

Replaces `anmol098/waka-readme-stats` with a local Python script that refreshes the `<!--START_SECTION:waka-->` … `<!--END_SECTION:waka-->` block in the repo root `README.md`.

## Prerequisites

- Python 3.12+
- [WakaTime API key](https://wakatime.com/settings/api)
- GitHub personal access token with `repo` and `read:user` (same as the old action’s `GH_TOKEN`)

## Local run

From the repository root (`piyushmishra318/`):

```bash
export WAKATIME_API_KEY="your-wakatime-api-key"
export GH_TOKEN="your-github-pat"

python -m pip install -r scripts/requirements.txt
python scripts/build_readme.py
```

On Windows (PowerShell):

```powershell
$env:WAKATIME_API_KEY = "your-wakatime-api-key"
$env:GH_TOKEN = "your-github-pat"
python -m pip install -r scripts/requirements.txt
python scripts/build_readme.py
```

The script updates `README.md` in place. Review the diff before committing.

## CI

`.github/workflows/update-readme.yml` runs daily at 18:30 UTC (00:00 IST) and on `workflow_dispatch`. Secrets: `WAKATIME_API_KEY`, `GH_TOKEN`.

## Out of scope (v1)

- Lines-of-code badge
- Quarterly LOC timeline / `bar_graph.png`
- Commit path filtering via `EXCLUDED_COMMIT_PATH_PATTERNS` (defined in `profile_config.py` for later use)
