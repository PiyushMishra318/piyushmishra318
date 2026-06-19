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

DAY_TIME_EMOJI = ("🌞", "🌆", "🌃", "🌙")
DAY_TIME_NAMES = ("Morning", "Daytime", "Evening", "Night")
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


def make_graph(percent: float) -> str:
    done, empty = "█", "░"
    quart = round(percent / 4)
    return f"{done * quart}{empty * (25 - quart)}"


def make_list(
    names: list[str],
    texts: list[str],
    percents: list[float],
    *,
    top_num: int = 5,
    sort: bool = True,
) -> str:
    rows = list(zip(names, texts, percents))
    if sort:
        rows = sorted(rows, key=lambda r: r[2], reverse=True)
    top = rows[:top_num]
    lines = []
    for name, text, percent in top:
        line = (
            f"{name[:25]}{' ' * (25 - len(name))}"
            f"{text}{' ' * (20 - len(text))}"
            f"{make_graph(percent)} {percent:05.2f} % "
        )
        lines.append(line)
    return "\n".join(lines)


def _naturalsize(num_bytes: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    size = float(num_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _intcomma(value: int) -> str:
    return f"{value:,}"


def _quote_lines(lines: list[str]) -> str:
    return "\n".join(f"> {line}" if line else ">" for line in lines)


def _section(title: str, body: str) -> str:
    body = body.rstrip()
    if not body:
        return ""
    return f"{title}\n\n{body}\n\n"


def _text_block(content: str) -> str:
    return f"```text\n{content.rstrip()}\n```"


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


def format_snapshot_block(
    user: dict[str, Any],
    contributions: dict[str, Any],
    repo_count: int,
) -> str:
    day_map = _contribution_day_map(contributions.get("contributions") or [])
    lines = ["**🐱 GitHub Snapshot**", ""]

    years = contributions.get("years") or []
    if years:
        year_row = years[0]
        lines.append(
            f"> 🏆 {_intcomma(int(year_row['total']))} contributions in {year_row['year']}"
        )

    last_7 = _rolling_contribution_sum(day_map, 7)
    last_30 = _rolling_contribution_sum(day_map, 30)
    lines.append(f"> 📈 {_intcomma(last_7)} last 7 days · {_intcomma(last_30)} last 30 days")

    current = _current_streak(day_map)
    longest = _longest_streak(day_map)
    lines.append(f"> 🔥 {_intcomma(current)} day streak · 🏅 {_intcomma(longest)} longest streak")

    lines.append(f"> 📂 {_intcomma(repo_count)} repos contributed to")

    disk_usage = user.get("disk_usage")
    if disk_usage is None:
        lines.append("> 📦 ? used in GitHub storage")
    else:
        lines.append(f"> 📦 {_naturalsize(disk_usage)} used in GitHub storage")

    public_repos = int(user.get("public_repos") or 0)
    private_repos = int(user.get("owned_private_repos") or 0)
    lines.append(f"> 📜 {public_repos} public · 🔑 {private_repos} private repos")

    if user.get("hireable"):
        lines.append("> 💼 Opted to hire")
    else:
        lines.append("> 🚫 Not opted to hire")

    return "\n".join(lines) + "\n"


def format_collaboration_block(stats: dict[str, int]) -> str:
    lines = [
        f"> 🔀 {_intcomma(stats['open_prs'])} open PRs · ✅ {_intcomma(stats['merged_prs'])} merged PRs",
        f"> 🐛 {_intcomma(stats['issues_opened'])} issues opened · 👀 {_intcomma(stats['reviews_given'])} reviews given",
    ]
    return _section("**🤝 Collaboration**", _quote_lines(lines))


def format_top_repos_block(scan: CommitScanResult, repositories: list[dict[str, Any]]) -> str:
    if not scan.repo_commit_counts:
        return ""

    ranked = sorted(scan.repo_commit_counts.items(), key=lambda item: item[1], reverse=True)[:5]
    total = sum(count for _, count in ranked)
    names = [_repo_display_name(name, repositories) for name, _ in ranked]
    texts = [f"{count} commits" for _, count in ranked]
    percents = [round(count / total * 100, 2) for _, count in ranked]

    return _section(
        "**🔥 Most Active Repos**",
        _text_block(make_list(names, texts, percents, sort=False)),
    )


def format_coding_rhythm_block(scan: CommitScanResult) -> str:
    parts: list[str] = []

    day_times = scan.day_times[1:] + scan.day_times[:1]
    sum_day = sum(day_times)
    if sum_day:
        early = sum(day_times[0:2]) >= sum(day_times[2:4])
        subtitle = "Early bird 🐤" if early else "Night owl 🦉"
        dt_names = [f"{DAY_TIME_EMOJI[i]} {DAY_TIME_NAMES[i]}" for i in range(4)]
        dt_texts = [f"{count} commits" for count in day_times]
        dt_percents = [round((count / sum_day) * 100, 2) for count in day_times]
        parts.append(
            _section(
                f"**⏰ When I Code** ({subtitle})",
                _text_block(make_list(dt_names, dt_texts, dt_percents, top_num=4, sort=False)),
            )
        )

    sum_week = sum(scan.week_days)
    if sum_week:
        weekday = sum(scan.week_days[0:5])
        weekend = sum(scan.week_days[5:7])
        weekend_pct = round(weekend / sum_week * 100, 2)
        weekday_pct = round(weekday / sum_week * 100, 2)
        best_day = WEEK_DAY_NAMES[scan.week_days.index(max(scan.week_days))]
        wd_names = list(WEEK_DAY_NAMES)
        wd_texts = [f"{count} commits" for count in scan.week_days]
        wd_percents = [round((count / sum_week) * 100, 2) for count in scan.week_days]

        rhythm_lines = [
            _text_block(make_list(wd_names, wd_texts, wd_percents, top_num=7, sort=False)),
            "",
            _text_block(
                make_list(
                    ["Weekday", "Weekend"],
                    [f"{weekday} commits", f"{weekend} commits"],
                    [weekday_pct, weekend_pct],
                    top_num=2,
                    sort=False,
                )
            ),
        ]
        parts.append(
            _section(
                f"**📅 Most Productive on {best_day}**",
                "\n".join(rhythm_lines),
            )
        )

    if scan.month_counts:
        busiest_key = max(scan.month_counts, key=scan.month_counts.get)
        year, month = busiest_key.split("-")
        busiest_name = MONTH_NAMES[int(month) - 1]
        month_ranked = sorted(scan.month_counts.items(), key=lambda item: item[1], reverse=True)[:5]
        month_total = sum(count for _, count in month_ranked)
        names = [MONTH_NAMES[int(key.split("-")[1]) - 1] for key, _ in month_ranked]
        texts = [f"{count} commits" for _, count in month_ranked]
        percents = [round(count / month_total * 100, 2) for _, count in month_ranked]
        parts.append(
            _section(
                f"**📆 Busiest Month: {busiest_name} {year}**",
                _text_block(make_list(names, texts, percents, sort=False)),
            )
        )

    return "\n".join(part for part in parts if part)


def format_language_block(repositories: list[dict[str, Any]]) -> str:
    language_count: dict[str, int] = {}

    for repo in repositories:
        if repo["name"] in IGNORED_REPOS or not repo.get("primaryLanguage"):
            continue
        language = repo["primaryLanguage"]["name"]
        language_count[language] = language_count.get(language, 0) + 1

    if not language_count:
        return ""

    total = sum(language_count.values())
    ranked = sorted(language_count.items(), key=lambda item: item[1], reverse=True)
    top_language = ranked[0][0]
    top = ranked[:5]
    names = [lang for lang, _ in top]
    texts = [f"{count} {'repo' if count == 1 else 'repos'}" for _, count in top]
    percents = [round(count / total * 100, 2) for _, count in top]

    return _section(
        f"**🧑‍💻 Mostly {top_language} Repos**",
        _text_block(make_list(names, texts, percents, sort=False)),
    )


def format_ai_manual_block(scan: CommitScanResult) -> str:
    total_commits = scan.ai_commits + scan.manual_commits
    total_lines = scan.ai_lines + scan.manual_lines
    if total_commits == 0:
        return ""

    commit_ai_pct = round(scan.ai_commits / total_commits * 100, 2)
    commit_manual_pct = round(100 - commit_ai_pct, 2)

    names = ["Manual commits", "AI-assisted commits"]
    texts = [
        f"{scan.manual_commits} commits",
        f"{scan.ai_commits} commits",
    ]
    percents = [commit_manual_pct, commit_ai_pct]

    body = _text_block(make_list(names, texts, percents, top_num=2, sort=False))

    if total_lines > 0:
        line_ai_pct = round(scan.ai_lines / total_lines * 100, 2)
        line_manual_pct = round(100 - line_ai_pct, 2)
        line_block = _text_block(
            make_list(
                ["Manual lines", "AI-assisted lines"],
                [f"{_intcomma(scan.manual_lines)} lines", f"{_intcomma(scan.ai_lines)} lines"],
                [line_manual_pct, line_ai_pct],
                top_num=2,
                sort=False,
            )
        )
        body = f"{body}\n\n{line_block}"

    note = (
        "> *AI-assisted share is estimated from commit messages "
        "(Copilot, Cursor, ChatGPT, etc.) — approximate, not exact.*"
    )
    return _section("**🤖 AI vs Manual**", f"{body}\n\n{note}")


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

    parts = [
        format_snapshot_block(user, contributions, repo_count),
        format_collaboration_block(collaboration),
        format_top_repos_block(scan, repositories),
        format_coding_rhythm_block(scan),
        format_language_block(repositories),
        format_ai_manual_block(scan),
    ]

    updated_at = datetime.now(timezone.utc)
    updated_iso = updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    updated_fallback = updated_at.strftime(UPDATED_DATE_FORMAT) + " UTC"
    parts.append(
        f" Last updated "
        f'<relative-time datetime="{updated_iso}" format="relative">{updated_fallback}</relative-time>'
    )
    return "\n".join(part for part in parts if part)


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
