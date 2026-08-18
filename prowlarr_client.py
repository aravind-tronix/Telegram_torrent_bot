from __future__ import annotations

import html
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import requests


@dataclass(frozen=True)
class TorrentResult:
    title: str
    indexer: str
    seeders: int
    leechers: int | None
    size: int | None
    link: str

    @property
    def size_label(self) -> str:
        return format_size(self.size)


def format_size(size: int | None) -> str:
    if size is None:
        return "unknown"
    value = float(size)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} TB"


def _int_or_zero(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _pick_link(item: dict[str, Any]) -> str:
    for key in ("magnetUrl", "downloadUrl", "guid", "infoUrl"):
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def extract_results(raw_items: list[dict[str, Any]], limit: int = 10) -> list[TorrentResult]:
    results: list[TorrentResult] = []
    for item in raw_items:
        link = _pick_link(item)
        title = str(item.get("title") or "").strip()
        if not title or not link:
            continue
        results.append(
            TorrentResult(
                title=title,
                indexer=str(item.get("indexer") or "unknown"),
                seeders=_int_or_zero(item.get("seeders")),
                leechers=_optional_int(item.get("leechers")),
                size=_optional_int(item.get("size")),
                link=link,
            )
        )
    results.sort(key=lambda r: r.seeders, reverse=True)
    return results[:limit]


def format_result(result: TorrentResult, number: int) -> str:
    leechers = "unknown" if result.leechers is None else str(result.leechers)
    return "\n".join(
        [
            f"<b>{number}. {html.escape(result.title)}</b>",
            f"Indexer: {html.escape(result.indexer)}",
            f"Seeders: {result.seeders} | Leechers: {leechers}",
            f"Size: {html.escape(result.size_label)}",
            f"<code>{html.escape(result.link)}</code>",
        ]
    )


class ProwlarrClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None, timeout: int = 30):
        self.base_url = (base_url or os.environ.get("PROWLARR_URL") or "http://127.0.0.1:9696").rstrip("/")
        self.api_key = api_key or os.environ.get("PROWLARR_API_KEY")
        if not self.api_key:
            raise ValueError("PROWLARR_API_KEY is required")
        self.timeout = timeout

    def search(self, query: str, limit: int = 10) -> list[TorrentResult]:
        query = query.strip()
        if not query:
            return []
        response = requests.get(
            urljoin(self.base_url + "/", "api/v1/search"),
            headers={"X-Api-Key": self.api_key},
            params={"query": query},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return extract_results(response.json(), limit=limit)
