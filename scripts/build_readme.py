#!/usr/bin/env python3
"""Build and replace the GitHub metrics section in profile README.md."""

from __future__ import annotations

import json
import os
import re
import sys
import time
import warnings
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from string import Template
from typing import Any

import httpx

from profile_config import (
    AI_COMMIT_MESSAGE_PATTERN,
    END_MARKER,
    GITHUB_USERNAME,
    GRAPHQL_PAGE_SIZE,
    IGNORED_REPOS,
    REPO_SLEEP_SECONDS,
    START_MARKER,
    UPDATED_DATE_FORMAT,
)

ROOT = Path(__file__).resolve().parent.parent
README_PATH = ROOT / "README.md"
CONTRIBUTIONS_API = f"https://github-contributions.vercel.app/api/v1/{GITHUB_USERNAME}"

WEEK_DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)

GITHUB_API_QUERIES = {
    "viewer_id": """
{
  user(login: "$username") {
    id
  }
}""",
    "user_collaboration_stats": """
{
  user(login: "$username") {
    openPullRequests: pullRequests(states: OPEN) { totalCount }
    mergedPullRequests: pullRequests(states: MERGED) { totalCount }
    issuesOpened: issues(states: [OPEN, CLOSED]) { totalCount }
    contributionsCollection(from: "2010-01-01T00:00:00Z", to: "$now") {
      pullRequestReviewContributions { totalCount }
    }
  }
}""",
    "repos_contributed_to": """
{
  user(login: "$username") {
    repositoriesContributedTo(
      orderBy: {field: CREATED_AT, direction: DESC},
      $pagination,
      includeUserRepositories: true
    ) {
      nodes {
        name
        owner { login }
        isFork
        isPrivate
        primaryLanguage { name }
      }
      pageInfo { endCursor hasNextPage }
    }
  }
}""",
    "user_repository_list": """
{
  user(login: "$username") {
    repositories(
      orderBy: {field: CREATED_AT, direction: DESC},
      $pagination,
      affiliations: [OWNER, COLLABORATOR],
      isFork: false
    ) {
      nodes {
        name
        owner { login }
        isPrivate
        primaryLanguage { name }
      }
      pageInfo { endCursor hasNextPage }
    }
  }
}""",
    "repo_branch_list": """
{
  repository(owner: "$owner", name: "$name") {
    refs(refPrefix: "refs/heads/", orderBy: {direction: DESC, field: TAG_COMMIT_DATE}, $pagination) {
      nodes { name }
      pageInfo { endCursor hasNextPage }
    }
  }
}""",
    "repo_commit_list": """
{
  repository(owner: "$owner", name: "$name") {
    ref(qualifiedName: "refs/heads/$branch") {
      target {
        ... on Commit {
          history(author: { id: "$id" }, $pagination) {
            nodes {
              ... on Commit {
                committedDate
                oid
                message
                additions
                deletions
              }
            }
            pageInfo { endCursor hasNextPage }
          }
        }
      }
    }
  }
}""",
}


@dataclass
class CommitScanResult:
    repo_commit_counts: dict[str, int] = field(default_factory=dict)
    month_counts: dict[str, int] = field(default_factory=dict)
    day_times: list[int] = field(default_factory=lambda: [0, 0, 0, 0])
    week_days: list[int] = field(default_factory=lambda: [0] * 7)
    ai_commits: int = 0
    manual_commits: int = 0
    ai_lines: int = 0
    manual_lines: int = 0


def _env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def replace_chunk(content: str, chunk: str) -> str:
    pattern = re.escape(START_MARKER) + r"[\s\S]*?" + re.escape(END_MARKER)
    replacement = f"{START_MARKER}\n{chunk.rstrip()}\n{END_MARKER}"
    if not re.search(pattern, content):
        raise SystemExit(f"README markers not found: {START_MARKER} ... {END_MARKER}")
    return re.sub(pattern, replacement, content, count=1)


def _intcomma(value: int) -> str:
    return f"{value:,}"


def _short_month(month_key: str) -> str:
    year, month = month_key.split("-")
    return f"{MONTH_NAMES[int(month) - 1][:3]} '{year[2:]}"


def _language_summary(repositories: list[dict[str, Any]], *, limit: int = 3) -> tuple[str, str]:
    language_count: dict[str, int] = {}
    for repo in repositories:
        if repo["name"] in IGNORED_REPOS or not repo.get("primaryLanguage"):
            continue
        language = repo["primaryLanguage"]["name"]
        language_count[language] = language_count.get(language, 0) + 1

    if not language_count:
        return "—", "—"

    ranked = sorted(language_count.items(), key=lambda item: item[1], reverse=True)
    top_language = ranked[0][0]
    stack = " · ".join(lang for lang, _ in ranked[:limit])
    return top_language, stack


def _top_repo_summary(
    scan: CommitScanResult,
    repositories: list[dict[str, Any]],
    *,
    limit: int = 3,
) -> str:
    if not scan.repo_commit_counts:
        return "—"

    ranked = sorted(scan.repo_commit_counts.items(), key=lambda item: item[1], reverse=True)[:limit]
    parts = []
    for name, count in ranked:
        label = _repo_display_name(name, repositories)
        if label.startswith("[private]"):
            label = name
        parts.append(f"`{label}` ({_intcomma(count)})")
    return " · ".join(parts)


def _rhythm_summary(scan: CommitScanResult) -> tuple[str, str, str, int]:
    day_times = scan.day_times[1:] + scan.day_times[:1]
    sum_day = sum(day_times)
    sum_week = sum(scan.week_days)

    if sum_day:
        early = sum(day_times[0:2]) >= sum(day_times[2:4])
        time_label = "early bird" if early else "night owl"
    else:
        time_label = "—"

    if sum_week:
        best_day = WEEK_DAY_NAMES[scan.week_days.index(max(scan.week_days))]
        weekend_pct = round(sum(scan.week_days[5:7]) / sum_week * 100)
    else:
        best_day = "—"
        weekend_pct = 0

    if scan.month_counts:
        busiest = _short_month(max(scan.month_counts, key=scan.month_counts.get))
    else:
        busiest = "—"

    return best_day, time_label, busiest, weekend_pct


def _ai_manual_summary(scan: CommitScanResult) -> tuple[int, int]:
    total_commits = scan.ai_commits + scan.manual_commits
    if total_commits == 0:
        return 0, 0
    ai_pct = round(scan.ai_commits / total_commits * 100)
    manual_pct = 100 - ai_pct
    return manual_pct, ai_pct


class GitHubClient:
    def __init__(self, token: str) -> None:
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }
        self._client = httpx.Client(timeout=60.0, headers=self._headers)
        self.user_node_id: str | None = None

    def close(self) -> None:
        self._client.close()

    def graphql(self, query_key: str, *, retries: int = 10, **kwargs: str) -> dict[str, Any]:
        body = {"query": Template(GITHUB_API_QUERIES[query_key]).substitute(kwargs)}
        response = self._client.post("https://api.github.com/graphql", json=body)
        if response.status_code == 200:
            payload = response.json()
            if payload.get("errors"):
                raise RuntimeError(json.dumps(payload["errors"])[:500])
            return payload

        if response.status_code in (502, 503, 504, 429, 403) and retries > 0:
            time.sleep(1.0)
            return self.graphql(query_key, retries=retries - 1, **kwargs)

        preview = (response.text or "")[:500]
        raise RuntimeError(f"GraphQL {query_key} failed HTTP {response.status_code}: {preview}")

    @staticmethod
    def _find_pagination_and_nodes(response: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if "nodes" in response and "pageInfo" in response:
            return response["nodes"], response["pageInfo"]
        if len(response) == 1:
            inner = response[next(iter(response))]
            if isinstance(inner, dict):
                return GitHubClient._find_pagination_and_nodes(inner)
        return [], {"hasNextPage": False}

    def graphql_paginated(self, query_key: str, **kwargs: str) -> list[dict[str, Any]]:
        first = self.graphql(query_key, pagination=f"first: {GRAPHQL_PAGE_SIZE}", **kwargs)
        data = first.get("data", {})
        nodes, page_info = self._find_pagination_and_nodes(data)

        while page_info.get("hasNextPage"):
            cursor = page_info["endCursor"]
            page = self.graphql(
                query_key,
                pagination=f'first: {GRAPHQL_PAGE_SIZE}, after: "{cursor}"',
                **kwargs,
            )
            new_nodes, page_info = self._find_pagination_and_nodes(page.get("data", {}))
            nodes.extend(new_nodes)

        return nodes

    def rest_user(self) -> dict[str, Any]:
        response = self._client.get("https://api.github.com/user")
        response.raise_for_status()
        return response.json()

    def viewer_node_id(self) -> str:
        if self.user_node_id:
            return self.user_node_id
        data = self.graphql("viewer_id", username=GITHUB_USERNAME, pagination="")
        self.user_node_id = data["data"]["user"]["id"]
        return self.user_node_id


def fetch_contributions_data() -> dict[str, Any]:
    response = httpx.get(CONTRIBUTIONS_API, timeout=60.0)
    response.raise_for_status()
    return response.json()


def _contribution_day_map(contributions: list[dict[str, Any]]) -> dict[date, int]:
    return {date.fromisoformat(row["date"]): int(row["count"]) for row in contributions}


def _rolling_contribution_sum(day_map: dict[date, int], days: int, *, end: date | None = None) -> int:
    end = end or datetime.now(timezone.utc).date()
    start = end - timedelta(days=days - 1)
    return sum(count for day, count in day_map.items() if start <= day <= end)


def _current_streak(day_map: dict[date, int], *, end: date | None = None) -> int:
    end = end or datetime.now(timezone.utc).date()
    cursor = end if day_map.get(end, 0) > 0 else end - timedelta(days=1)
    streak = 0
    while day_map.get(cursor, 0) > 0:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _longest_streak(day_map: dict[date, int]) -> int:
    best = 0
    run = 0
    previous: date | None = None
    for day in sorted(day for day, count in day_map.items() if count > 0):
        if previous and (day - previous).days == 1:
            run += 1
        else:
            run = 1
        best = max(best, run)
        previous = day
    return best


def _is_ai_assisted_commit(message: str | None) -> bool:
    if not message:
        return False
    return bool(AI_COMMIT_MESSAGE_PATTERN.search(message))


def collect_repositories(gh: GitHubClient) -> list[dict[str, Any]]:
    owned = gh.graphql_paginated("user_repository_list", username=GITHUB_USERNAME)
    names = {repo["name"] for repo in owned}
    contributed = gh.graphql_paginated("repos_contributed_to", username=GITHUB_USERNAME)
    extra = [
        repo
        for repo in contributed
        if repo and repo["name"] not in names and not repo.get("isFork")
    ]
    return owned + extra


def _count_active_repositories(repositories: list[dict[str, Any]]) -> int:
    return sum(
        1
        for repo in repositories
        if repo and repo["name"] not in IGNORED_REPOS and not repo.get("isFork")
    )


def _repo_label(repo: dict[str, Any]) -> str:
    if repo.get("isPrivate"):
        return "[private]"
    owner = repo.get("owner", {}).get("login", "?")
    return f"{owner}/{repo.get('name', '?')}"


def _repo_display_name(repo_name: str, repositories: list[dict[str, Any]]) -> str:
    for repo in repositories:
        if repo["name"] == repo_name:
            return _repo_label(repo)
    return repo_name


def scan_commits(gh: GitHubClient, repositories: list[dict[str, Any]]) -> CommitScanResult:
    author_id = gh.viewer_node_id()
    result = CommitScanResult()
    seen_oids: set[str] = set()

    for index, repo in enumerate(repositories):
        if repo["name"] in IGNORED_REPOS or repo.get("isFork"):
            continue

        label = _repo_label(repo)
        print(f"  {index + 1}/{len(repositories)} Retrieving repo: {label}", flush=True)
        owner = repo["owner"]["login"]
        repo_unique_commits = 0

        try:
            branches = gh.graphql_paginated(
                "repo_branch_list",
                owner=owner,
                name=repo["name"],
            )
        except Exception as exc:
            warnings.warn(f"Skipping repo {label}: {exc}")
            continue

        if not branches:
            warnings.warn(f"Skipping repo {label}: no branches")
            continue

        for branch in branches:
            try:
                commits = gh.graphql_paginated(
                    "repo_commit_list",
                    owner=owner,
                    name=repo["name"],
                    branch=branch["name"],
                    id=author_id,
                )
            except Exception as exc:
                warnings.warn(
                    f"Skipping branch {label}@{branch.get('name', '?')}: {exc}"
                )
                continue

            for commit in commits:
                oid = commit["oid"]
                if oid in seen_oids:
                    continue
                seen_oids.add(oid)
                repo_unique_commits += 1

                committed = datetime.strptime(
                    commit["committedDate"], "%Y-%m-%dT%H:%M:%SZ"
                ).replace(tzinfo=timezone.utc)
                bucket = committed.hour // 6
                result.day_times[bucket] += 1
                result.week_days[committed.isoweekday() - 1] += 1
                month_key = committed.strftime("%Y-%m")
                result.month_counts[month_key] = result.month_counts.get(month_key, 0) + 1

                lines_changed = int(commit.get("additions") or 0) + int(commit.get("deletions") or 0)
                if _is_ai_assisted_commit(commit.get("message")):
                    result.ai_commits += 1
                    result.ai_lines += lines_changed
                else:
                    result.manual_commits += 1
                    result.manual_lines += lines_changed

        if repo_unique_commits:
            result.repo_commit_counts[repo["name"]] = repo_unique_commits

        time.sleep(REPO_SLEEP_SECONDS)

    return result


def fetch_collaboration_stats(gh: GitHubClient) -> dict[str, int]:
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = gh.graphql("user_collaboration_stats", username=GITHUB_USERNAME, now=now_iso)
    user = payload["data"]["user"]
    reviews = user["contributionsCollection"]["pullRequestReviewContributions"]["totalCount"]
    return {
        "open_prs": user["openPullRequests"]["totalCount"],
        "merged_prs": user["mergedPullRequests"]["totalCount"],
        "issues_opened": user["issuesOpened"]["totalCount"],
        "reviews_given": reviews,
    }


def format_compact_dashboard(
    user: dict[str, Any],
    contributions: dict[str, Any],
    repo_count: int,
    collaboration: dict[str, int],
    scan: CommitScanResult,
    repositories: list[dict[str, Any]],
) -> str:
    day_map = _contribution_day_map(contributions.get("contributions") or [])
    years = contributions.get("years") or []
    year_total = int(years[0]["total"]) if years else 0
    year_label = years[0]["year"] if years else datetime.now(timezone.utc).year

    last_7 = _rolling_contribution_sum(day_map, 7)
    last_30 = _rolling_contribution_sum(day_map, 30)
    current = _current_streak(day_map)
    longest = _longest_streak(day_map)

    public_repos = int(user.get("public_repos") or 0)
    hireable = "Open to hire" if user.get("hireable") else "Not hiring"

    best_day, time_label, busiest_month, weekend_pct = _rhythm_summary(scan)
    top_language, language_stack = _language_summary(repositories)
    manual_pct, ai_pct = _ai_manual_summary(scan)
    top_repos = _top_repo_summary(scan, repositories)

    lines = [
        "**GitHub at a glance**",
        "",
        (
            f"> 🏆 **{_intcomma(year_total)}** contributions ({year_label}) · "
            f"**{_intcomma(last_7)}** / 7d · **{_intcomma(last_30)}** / 30d · "
            f"streak **{_intcomma(current)}** (best **{_intcomma(longest)}**)"
        ),
        (
            f"> 🤝 **{_intcomma(collaboration['merged_prs'])}** merged · "
            f"**{_intcomma(collaboration['open_prs'])}** open PRs · "
            f"**{_intcomma(collaboration['issues_opened'])}** issues · "
            f"**{_intcomma(collaboration['reviews_given'])}** reviews · "
            f"**{_intcomma(repo_count)}** repos · **{public_repos}** public · {hireable}"
        ),
        (
            f"> ⏰ peak **{best_day}** · {time_label} · "
            f"busiest **{busiest_month}** · weekend **{weekend_pct}%**"
        ),
        (
            f"> 💻 mostly **{top_language}** ({language_stack}) · "
            f"manual **{manual_pct}%** / AI **{ai_pct}%** *"
        ),
        f"> 🔥 {top_repos}",
        "> *AI share estimated from commit messages — approximate.*",
    ]

    updated_at = datetime.now(timezone.utc)
    updated_iso = updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    updated_fallback = updated_at.strftime(UPDATED_DATE_FORMAT) + " UTC"
    lines.extend(
        [
            "",
            (
                f"Updated "
                f'<relative-time datetime="{updated_iso}" format="relative">'
                f"{updated_fallback}</relative-time>"
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def build_section(gh_token: str) -> str:
    gh = GitHubClient(gh_token)
    try:
        user = gh.rest_user()
        contributions = fetch_contributions_data()
        repositories = collect_repositories(gh)
        repo_count = _count_active_repositories(repositories)
        collaboration = fetch_collaboration_stats(gh)
        scan = scan_commits(gh, repositories)
    finally:
        gh.close()

    return format_compact_dashboard(
        user,
        contributions,
        repo_count,
        collaboration,
        scan,
        repositories,
    )


def main() -> None:
    gh_token = _env("GH_TOKEN")

    readme = README_PATH.read_text(encoding="utf-8")
    section = build_section(gh_token)
    README_PATH.write_text(replace_chunk(readme, section), encoding="utf-8")
    print(f"Updated {README_PATH}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except httpx.HTTPStatusError as exc:
        print(f"HTTP error: {exc.response.status_code} {exc.request.url}", file=sys.stderr)
        raise SystemExit(1) from exc
