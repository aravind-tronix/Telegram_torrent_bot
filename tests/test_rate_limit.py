import pytest

from app import message_interval_seconds, send_results
from prowlarr_client import TorrentResult


class FakeMessage:
    def __init__(self):
        self.sent = []

    async def reply_html(self, text, **kwargs):
        self.sent.append((text, kwargs))


class FakeUpdate:
    def __init__(self):
        self.effective_message = FakeMessage()


@pytest.mark.asyncio
async def test_send_results_waits_between_multiple_messages():
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    results = [
        TorrentResult(f"title {i}", "Indexer", 10 - i, 0, 1024, f"magnet:?xt={i}")
        for i in range(3)
    ]
    update = FakeUpdate()

    await send_results(update, results, delay_seconds=1.25, sleeper=fake_sleep)

    assert len(update.effective_message.sent) == 3
    assert sleeps == [1.25, 1.25]


def test_message_interval_has_safe_default_and_bounds(monkeypatch):
    monkeypatch.delenv("BOT_MESSAGE_INTERVAL_SECONDS", raising=False)
    assert message_interval_seconds() == 1.1

    monkeypatch.setenv("BOT_MESSAGE_INTERVAL_SECONDS", "0")
    assert message_interval_seconds() == 0.5

    monkeypatch.setenv("BOT_MESSAGE_INTERVAL_SECONDS", "99")
    assert message_interval_seconds() == 5.0
