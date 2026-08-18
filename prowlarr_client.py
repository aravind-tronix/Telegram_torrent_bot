from __future__ import annotations

import hashlib
import html
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urljoin, urlparse

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


def is_magnet(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("magnet:")


def is_local_prowlarr_download(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.hostname in {"127.0.0.1", "localhost"} and parsed.path.endswith("/download")


def _pick_magnet(item: dict[str, Any]) -> str:
    # Prowlarr can put a real magnet in guid while magnetUrl/downloadUrl is its local proxy.
    for key in ("magnetUrl", "downloadUrl", "guid", "infoUrl"):
        value = item.get(key)
        if is_magnet(value):
            return str(value)
    return ""


class BencodeError(ValueError):
    pass


def _bdecode(data: bytes, pos: int = 0) -> tuple[Any, int]:
    if pos >= len(data):
        raise BencodeError("unexpected end of bencode")
    marker = data[pos:pos + 1]
    if marker == b"i":
        end = data.index(b"e", pos)
        return int(data[pos + 1:end]), end + 1
    if marker == b"l":
        pos += 1
        out = []
        while data[pos:pos + 1] != b"e":
            value, pos = _bdecode(data, pos)
            out.append(value)
        return out, pos + 1
    if marker == b"d":
        pos += 1
        out = {}
        while data[pos:pos + 1] != b"e":
            key, pos = _bdecode(data, pos)
            value, pos = _bdecode(data, pos)
            out[key] = value
        return out, pos + 1
    if marker.isdigit():
        colon = data.index(b":", pos)
        length = int(data[pos:colon])
        start = colon + 1
        end = start + length
        return data[start:end], end
    raise BencodeError(f"invalid bencode marker at {pos}")


def _bencode(value: Any) -> bytes:
    if isinstance(value, int):
        return b"i" + str(value).encode() + b"e"
    if isinstance(value, bytes):
        return str(len(value)).encode() + b":" + value
    if isinstance(value, str):
        return _bencode(value.encode())
    if isinstance(value, list):
        return b"l" + b"".join(_bencode(v) for v in value) + b"e"
    if isinstance(value, dict):
        out = b"d"
        for key in sorted(value):
            out += _bencode(key) + _bencode(value[key])
        return out + b"e"
    raise TypeError(value)


def _decode_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return str(value)


def magnet_from_torrent_bytes(torrent_bytes: bytes, display_name: str | None = None) -> str:
    torrent, pos = _bdecode(torrent_bytes)
    if pos > len(torrent_bytes) or not isinstance(torrent, dict):
        raise BencodeError("invalid torrent payload")
    info = torrent.get(b"info")
    if not isinstance(info, dict):
        raise BencodeError("torrent missing info dictionary")

    info_hash = hashlib.sha1(_bencode(info)).hexdigest()
    pieces = [f"xt=urn:btih:{info_hash}"]
    name = display_name or _decode_text(info.get(b"name", ""))
    if name:
        pieces.append("dn=" + quote(name))
    announce = torrent.get(b"announce")
    trackers: list[str] = []
    if announce:
        trackers.append(_decode_text(announce))
    announce_list = torrent.get(b"announce-list")
    if isinstance(announce_list, list):
        for tier in announce_list:
            if isinstance(tier, list):
                for tracker in tier:
                    tracker_text = _decode_text(tracker)
                    if tracker_text and tracker_text not in trackers:
                        trackers.append(tracker_text)
    pieces.extend("tr=" + quote(tracker, safe="") for tracker in trackers)
    return "magnet:?" + "&".join(pieces)


def extract_results(raw_items: list[dict[str, Any]], limit: int = 10) -> list[TorrentResult]:
    results: list[TorrentResult] = []
    for item in raw_items:
        link = _pick_magnet(item)
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

    def _resolve_download_to_magnet(self, item: dict[str, Any]) -> str:
        download_url = item.get("downloadUrl") or item.get("magnetUrl")
        if not isinstance(download_url, str) or not is_local_prowlarr_download(download_url):
            return ""
        response = requests.get(download_url, timeout=self.timeout, allow_redirects=False)
        response.raise_for_status()
        redirect_location = response.headers.get("location") or response.headers.get("Location")
        if is_magnet(redirect_location):
            return str(redirect_location)
        content_type = response.headers.get("content-type", "")
        if isinstance(response.url, str) and response.url.startswith("magnet:"):
            return response.url
        if "torrent" not in content_type and not response.content.startswith(b"d"):
            return ""
        return magnet_from_torrent_bytes(response.content, display_name=str(item.get("title") or ""))

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
        raw_items = response.json()
        for item in raw_items:
            if _pick_magnet(item):
                continue
            try:
                magnet = self._resolve_download_to_magnet(item)
            except Exception:
                continue
            if magnet:
                item["magnetUrl"] = magnet
        return extract_results(raw_items, limit=limit)
