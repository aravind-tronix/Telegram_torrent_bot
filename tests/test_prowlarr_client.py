from prowlarr_client import TorrentResult, extract_results, format_result


def test_extract_results_sorts_by_seeders_and_keeps_magnet():
    raw = [
        {
            "title": "Low seed",
            "indexer": "YTS",
            "seeders": 2,
            "leechers": 1,
            "size": 1024,
            "magnetUrl": "magnet:?xt=low",
            "downloadUrl": "https://example.test/low.torrent",
        },
        {
            "title": "High seed",
            "indexer": "TPB",
            "seeders": 50,
            "leechers": 3,
            "size": 2048,
            "downloadUrl": "magnet:?xt=high",
        },
    ]

    results = extract_results(raw, limit=2)

    assert [r.title for r in results] == ["High seed", "Low seed"]
    assert results[0].link == "magnet:?xt=high"
    assert results[0].size_label == "2.0 KB"


def test_format_result_escapes_html_for_telegram():
    result = TorrentResult(
        title="A <bad> & movie",
        indexer="TPB",
        seeders=5,
        leechers=2,
        size=1536,
        link="magnet:?xt=urn:test&dn=A&B",
    )

    text = format_result(result, 1)

    assert "<b>1. A &lt;bad&gt; &amp; movie</b>" in text
    assert "Indexer: TPB" in text
    assert "Seeders: 5" in text
    assert "1.5 KB" in text
    assert "<code>magnet:?xt=urn:test&amp;dn=A&amp;B</code>" in text
