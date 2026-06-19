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

### Metrics layout

One compact **GitHub at a glance** block (~6 lines): activity, collaboration, rhythm, languages, AI split, and top repos. No ASCII charts — designed to fit above the fold with the bio.

## CI

`.github/workflows/update-readme.yml` runs daily at 18:30 UTC (00:00 IST) and on `workflow_dispatch`. Secret: `GH_TOKEN`.

## Profile view counter

The README uses [GitViews](https://gitviews.com) — the badge increments on each profile load (same idea as komarev).

```markdown
![](https://gitviews.com/user/piyushmishra318.svg?style=for-the-badge&label-color=555555&color=0e75b6)
```

To carry over an old total, add `?base=1234` to the URL permanently.

## Out of scope (v1)

- Lines-of-code badge
- Quarterly LOC timeline / `bar_graph.png`
- Commit path filtering via `EXCLUDED_COMMIT_PATH_PATTERNS` (defined in `profile_config.py` for later use)
