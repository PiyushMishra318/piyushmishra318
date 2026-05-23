"""Configuration for the profile README metrics builder."""

from __future__ import annotations

import re

GITHUB_USERNAME = "piyushmishra318"
WAKATIME_API_URL = "https://wakatime.com/api/v1/"

# From .github/workflows/wakatime.yaml (deduplicated).
IGNORED_REPOS: set[str] = {
    "asdb",
    "mypro",
    "newprojects",
    "myprojects",
    "age-calc",
    "colorgenerator",
    "basic",
    "sample",
    "test",
    "cfs",
    "abcd",
    "cfs-history-17-jan-2023",
    "concord",
    "testing",
    "ebmpapst",
    "bulgin",
    "subhas",
    "carlogavazzi",
    "adityatest1",
    "instockav6",
    "testing14",
    "instockav5",
    "instockav4",
    "microtest1",
    "cotek",
    "instockav3",
    "synctest",
    "draftlogin1",
    "draftlogin",
    "test122",
}

# Reserved for future commit filtering (not used in v1).
EXCLUDED_COMMIT_PATH_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"package-lock\.json$"),
    re.compile(r"yarn\.lock$"),
    re.compile(r"pnpm-lock\.yaml$"),
    re.compile(r"node_modules/"),
]

SECTION_NAME = "waka"
UPDATED_DATE_FORMAT = "%d/%m/%Y %H:%M:%S"

START_MARKER = f"<!--START_SECTION:{SECTION_NAME}-->"
END_MARKER = f"<!--END_SECTION:{SECTION_NAME}-->"

BADGE_STYLE = "flat"
REPO_SLEEP_SECONDS = 0.4
GRAPHQL_PAGE_SIZE = 100
