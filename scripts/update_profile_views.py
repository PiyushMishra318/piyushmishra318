#!/usr/bin/env python3
"""Update self-hosted profile view badge from GitHub traffic insights."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

from profile_config import GITHUB_USERNAME

ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT / "assets"
DATA_PATH = ASSETS_DIR / "profile-views.json"
SVG_PATH = ASSETS_DIR / "profile-views.svg"

BADGE_LABEL = "Profile views"
BADGE_COLOR = "#0e75b6"
LABEL_COLOR = "#555555"


def _env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def _load_data() -> dict:
    if DATA_PATH.exists():
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return {"base": 0, "total": 0, "days": {}}


def _save_data(data: dict) -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _fetch_traffic(token: str) -> dict:
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_USERNAME}/traffic/views"
    response = httpx.get(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        timeout=60.0,
    )
    response.raise_for_status()
    return response.json()


def _merge_traffic(data: dict, traffic: dict) -> int:
    days: dict[str, int] = data.setdefault("days", {})
    total = int(data.get("total") or 0)

    for entry in traffic.get("views") or []:
        day = str(entry["timestamp"])[:10]
        count = int(entry["count"])
        previous = int(days.get(day) or 0)
        if count > previous:
            total += count - previous
            days[day] = count

    data["total"] = total
    return int(data.get("base") or 0) + total


def _format_count(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M".replace(".0M", "M")
    if value >= 1_000:
        return f"{value / 1_000:.1f}K".replace(".0K", "K")
    return str(value)


def _estimate_text_width(text: str, *, bold: bool = False) -> int:
    scale = 7.2 if bold else 6.8
    return max(int(len(text) * scale) + 12, 24)


def _render_badge(count: int) -> str:
    label = BADGE_LABEL
    value = _format_count(count)
    label_width = _estimate_text_width(label, bold=True)
    value_width = _estimate_text_width(value, bold=True)
    width = label_width + value_width

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="28" role="img" aria-label="{label}: {value}">
  <title>{label}: {count:,}</title>
  <g shape-rendering="crispEdges">
    <rect width="{label_width}" height="28" fill="{LABEL_COLOR}"/>
    <rect x="{label_width}" width="{value_width}" height="28" fill="{BADGE_COLOR}"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="11" font-weight="700">
    <text x="{label_width / 2:.1f}" y="18.5">{label}</text>
    <text x="{label_width + value_width / 2:.1f}" y="18.5">{value}</text>
  </g>
</svg>
"""


def main() -> None:
    token = _env("GH_TOKEN")
    data = _load_data()
    traffic = _fetch_traffic(token)
    display_count = _merge_traffic(data, traffic)
    _save_data(data)
    SVG_PATH.write_text(_render_badge(display_count), encoding="utf-8")
    print(
        f"Updated profile views badge: {display_count:,} "
        f"(base={int(data.get('base') or 0):,}, tracked={int(data.get('total') or 0):,})",
        flush=True,
    )


if __name__ == "__main__":
    try:
        main()
    except httpx.HTTPStatusError as exc:
        print(f"HTTP error: {exc.response.status_code} {exc.request.url}", file=sys.stderr)
        raise SystemExit(1) from exc
