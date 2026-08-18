from unittest.mock import Mock, patch

from prowlarr_client import ProwlarrClient, extract_results, magnet_from_torrent_bytes


def benc(value):
    if isinstance(value, int):
        return b"i" + str(value).encode() + b"e"
    if isinstance(value, bytes):
        return str(len(value)).encode() + b":" + value
    if isinstance(value, str):
        return benc(value.encode())
    if isinstance(value, list):
        return b"l" + b"".join(benc(v) for v in value) + b"e"
    if isinstance(value, dict):
        out = b"d"
        for k in sorted(value):
            out += benc(k) + benc(value[k])
        return out + b"e"
    raise TypeError(value)


def test_extract_results_prefers_real_magnet_over_local_proxy():
    raw = [
        {
            "title": "Ubuntu",
            "indexer": "Nyaa.si",
            "seeders": 1,
            "magnetUrl": "http://127.0.0.1:9696/2/download?apikey=secret",
            "downloadUrl": "http://127.0.0.1:9696/2/download?apikey=secret",
            "guid": "magnet:?xt=urn:btih:ABC123&dn=Ubuntu",
        }
    ]

    results = extract_results(raw)

    assert len(results) == 1
    assert results[0].link == "magnet:?xt=urn:btih:ABC123&dn=Ubuntu"


def test_extract_results_skips_local_proxy_when_no_magnet_available():
    raw = [
        {
            "title": "Proxy only",
            "indexer": "Torrent Downloads",
            "seeders": 1,
            "downloadUrl": "http://127.0.0.1:9696/4/download?apikey=secret",
            "guid": "https://example.test/detail",
        }
    ]

    assert extract_results(raw) == []


def test_magnet_from_torrent_bytes_builds_btih_from_info_dict():
    torrent = benc(
        {
            "announce": "udp://tracker.example/announce",
            "info": {
                "name": "ubuntu.iso",
                "piece length": 16384,
                "length": 123,
                "pieces": b"0" * 20,
            },
        }
    )

    magnet = magnet_from_torrent_bytes(torrent, display_name="ubuntu.iso")

    assert magnet.startswith("magnet:?xt=urn:btih:")
    assert "&dn=ubuntu.iso" in magnet
    assert "&tr=udp%3A%2F%2Ftracker.example%2Fannounce" in magnet


def test_prowlarr_resolver_uses_magnet_redirect_location():
    response = Mock()
    response.status_code = 301
    response.headers = {"location": "magnet:?xt=urn:btih:REDIRECTED"}
    response.raise_for_status.return_value = None

    client = ProwlarrClient(base_url="http://127.0.0.1:9696", api_key="test")
    with patch("prowlarr_client.requests.get", return_value=response) as get:
        magnet = client._resolve_download_to_magnet(
            {"downloadUrl": "http://127.0.0.1:9696/4/download?apikey=test", "title": "x"}
        )

    assert magnet == "magnet:?xt=urn:btih:REDIRECTED"
    assert get.call_args.kwargs["allow_redirects"] is False
