#!/usr/bin/env python3
"""Build and replace the GitHub metrics section in profile README.md."""

from __future__ import annotations

import json
import os
import re
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from string import Template
from typing import Any

import httpx

from profile_config import (
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

DAY_TIME_EMOJI = ("🌞", "🌆", "🌃", "🌙")
DAY_TIME_NAMES = ("Morning", "Daytime", "Evening", "Night")
WEEK_DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

GITHUB_API_QUERIES = {
    "viewer_id": """
{
  user(login: "$username") {
    id
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
    top = sorted(rows[:top_num], key=lambda r: r[2], reverse=True) if sort else rows[:top_num]
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



def fetch_github_short_stats(gh: GitHubClient) -> str:
    user = gh.rest_user()
    stats_response = httpx.get(
        f"https://github-contributions.vercel.app/api/v1/{GITHUB_USERNAME}",
        timeout=60.0,
    )
    stats_response.raise_for_status()
    contributions = stats_response.json()

    lines = ["**🐱 My GitHub Data** ", ""]

    disk_usage = user.get("disk_usage")
    if disk_usage is None:
        lines.append("> 📦 ? Used in GitHub's Storage ")
    else:
        lines.append(f"> 📦 {_naturalsize(disk_usage)} Used in GitHub's Storage ")
    lines.append(" > ")

    years = contributions.get("years") or []
    if years:
        year_row = years[0]
        lines.append(
            f"> 🏆 {_intcomma(int(year_row['total']))} Contributions in the Year {year_row['year']}"
        )
        lines.append(" > ")

    if user.get("hireable"):
        lines.append("> 💼 Opted to Hire")
    else:
        lines.append("> 🚫 Not Opted to Hire")
    lines.append(" > ")

    public_repos = int(user.get("public_repos") or 0)
    public_label = "Public Repositories" if public_repos != 1 else "Public Repository"
    lines.append(f"> 📜 {public_repos} {public_label} ")
    lines.append(" > ")

    private_repos = int(user.get("owned_private_repos") or 0)
    private_label = "Private Repositories" if private_repos != 1 else "Private Repository"
    lines.append(f"> 🔑 {private_repos} {private_label} ")
    lines.append(" > ")

    return "\n".join(lines) + "\n"


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


def _repo_label(repo: dict[str, Any]) -> str:
    if repo.get("isPrivate"):
        return "[private]"
    owner = repo.get("owner", {}).get("login", "?")
    return f"{owner}/{repo.get('name', '?')}"


def fetch_commit_time_stats(gh: GitHubClient, repositories: list[dict[str, Any]]) -> str:
    author_id = gh.viewer_node_id()
    commit_dates: dict[str, dict[str, dict[str, str]]] = {}

    for index, repo in enumerate(repositories):
        if repo["name"] in IGNORED_REPOS or repo.get("isFork"):
            continue

        label = _repo_label(repo)
        print(f"  {index + 1}/{len(repositories)} Retrieving repo: {label}", flush=True)
        owner = repo["owner"]["login"]
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
                repo_dates = commit_dates.setdefault(repo["name"], {})
                branch_dates = repo_dates.setdefault(branch["name"], {})
                branch_dates[commit["oid"]] = commit["committedDate"]

        time.sleep(REPO_SLEEP_SECONDS)

    return format_commit_time_stats(commit_dates)


def format_commit_time_stats(
    commit_dates: dict[str, dict[str, dict[str, str]]],
) -> str:
    day_times = [0, 0, 0, 0]
    week_days = [0] * 7

    for repo_commits in commit_dates.values():
        for branch_commits in repo_commits.values():
            for committed_date in branch_commits.values():
                local_date = datetime.strptime(committed_date, "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=timezone.utc
                )
                day_times[local_date.hour // 6] += 1
                week_days[local_date.isoweekday() - 1] += 1

    day_times = day_times[1:] + day_times[:1]
    sum_day = sum(day_times)
    sum_week = sum(week_days)

    parts: list[str] = []

    if sum_day:
        early = sum(day_times[0:2]) >= sum(day_times[2:4])
        title = "**I'm an Early 🐤** " if early else "**I'm a Night 🦉** "
        dt_names = [f"{DAY_TIME_EMOJI[i]} {DAY_TIME_NAMES[i]}" for i in range(4)]
        dt_texts = [f"{count} commits" for count in day_times]
        dt_percents = [round((count / sum_day) * 100, 2) for count in day_times]
        parts.append(title)
        parts.append("")
        parts.append("```text")
        parts.append(
            make_list(dt_names, dt_texts, dt_percents, top_num=7, sort=False)
        )
        parts.append("```")

    if sum_week:
        wd_names = list(WEEK_DAY_NAMES)
        wd_texts = [f"{count} commits" for count in week_days]
        wd_percents = [round((count / sum_week) * 100, 2) for count in week_days]
        best_day = wd_names[wd_percents.index(max(wd_percents))]
        parts.append(f"📅 **I'm Most Productive on {best_day}** ")
        parts.append("")
        parts.append("```text")
        parts.append(
            make_list(wd_names, wd_texts, wd_percents, top_num=7, sort=False)
        )
        parts.append("```")

    if parts:
        parts.append("")
        parts.append("")
    return "\n".join(parts)


def fetch_language_per_repo(repositories: list[dict[str, Any]]) -> str:
    language_count: dict[str, dict[str, int]] = {}
    repos_with_language = [repo for repo in repositories if repo.get("primaryLanguage")]

    for repo in repos_with_language:
        if repo["name"] in IGNORED_REPOS:
            continue
        language = repo["primaryLanguage"]["name"]
        language_count.setdefault(language, {"count": 0})
        language_count[language]["count"] += 1

    if not language_count:
        return ""

    names = list(language_count.keys())
    texts = [
        f"{language_count[lang]['count']} "
        f"{'repo' if language_count[lang]['count'] == 1 else 'repos'}"
        for lang in names
    ]
    total = len(repos_with_language)
    percents = [round(language_count[lang]["count"] / total * 100, 2) for lang in names]
    top_language = max(language_count, key=lambda lang: language_count[lang]["count"])

    return (
        f"**I Mostly Code in {top_language}** \n\n"
        f"```text\n{make_list(names, texts, percents)}\n```\n\n"
    )


def build_section(gh_token: str) -> str:
    parts: list[str] = []

    gh = GitHubClient(gh_token)
    try:
        parts.append(fetch_github_short_stats(gh))
        repositories = collect_repositories(gh)
        parts.append(fetch_commit_time_stats(gh, repositories))
        parts.append(fetch_language_per_repo(repositories))
    finally:
        gh.close()

    updated = datetime.now(timezone.utc).strftime(UPDATED_DATE_FORMAT)
    parts.append(f"\n Last Updated on {updated} UTC")
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
