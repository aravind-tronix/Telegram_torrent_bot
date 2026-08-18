import asyncio

from scripts.broadcast_alive import BroadcastStats, DEFAULT_MESSAGE, iter_chat_ids, run_broadcast


class FakeCollection:
    def __init__(self, docs):
        self.docs = docs
        self.deleted = []

    def find(self, query, projection):
        assert query == {"chat_id": {"$exists": True}}
        assert projection == {"_id": 0, "chat_id": 1}
        return iter(self.docs)

    def delete_one(self, query):
        self.deleted.append(query)


class FakeBot:
    def __init__(self, failing_ids=None):
        self.failing_ids = set(failing_ids or [])
        self.sent = []

    async def send_message(self, chat_id, text, disable_web_page_preview=True):
        if chat_id in self.failing_ids:
            raise RuntimeError("blocked")
        self.sent.append((chat_id, text, disable_web_page_preview))


async def fake_sleep(seconds):
    fake_sleep.calls.append(seconds)


fake_sleep.calls = []


def test_default_message_tells_users_to_restart_and_use_bot():
    assert "/start" in DEFAULT_MESSAGE
    assert "/search" in DEFAULT_MESSAGE
    assert "restart" in DEFAULT_MESSAGE.lower()
    assert "Read me" in DEFAULT_MESSAGE
    assert "https://t.me/Torrent_link_bot" in DEFAULT_MESSAGE
    assert "share" in DEFAULT_MESSAGE.lower()


def test_iter_chat_ids_dedupes_and_ignores_bad_rows():
    docs = [
        {"chat_id": 1},
        {"chat_id": "2"},
        {"chat_id": 1},
        {"chat_id": None},
        {"bad": 3},
    ]

    assert list(iter_chat_ids(FakeCollection(docs))) == [1, 2]


def test_run_broadcast_dry_run_sends_nothing():
    bot = FakeBot()
    stats = asyncio.run(
        run_broadcast(
            chat_ids=[1, 2],
            bot=bot,
            message="Bot is back alive.",
            execute=False,
            delay_seconds=0,
            sleeper=fake_sleep,
        )
    )

    assert stats == BroadcastStats(total=2, sent=0, failed=0, skipped=2)
    assert bot.sent == []


def test_run_broadcast_execute_sends_with_delay_and_counts_failures():
    fake_sleep.calls = []
    bot = FakeBot(failing_ids={2})
    collection = FakeCollection([])
    stats = asyncio.run(
        run_broadcast(
            chat_ids=[1, 2, 3],
            bot=bot,
            collection=collection,
            message="Bot is back alive.",
            execute=True,
            delay_seconds=1.5,
            sleeper=fake_sleep,
        )
    )

    assert stats == BroadcastStats(total=3, sent=2, failed=1, skipped=0)
    assert [row[0] for row in bot.sent] == [1, 3]
    assert collection.deleted == [{"chat_id": 2}]
    assert fake_sleep.calls == [1.5, 1.5]
