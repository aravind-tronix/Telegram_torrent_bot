import pytest

from app import free_text_search, remember_chat_id


class FakeStore:
    def __init__(self):
        self.chat_ids = []

    def ensure_user(self, chat_id):
        self.chat_ids.append(chat_id)
        return True


class FakeChat:
    def __init__(self, chat_id, chat_type="private"):
        self.id = chat_id
        self.type = chat_type


class FakeMessage:
    def __init__(self, text=""):
        self.text = text
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(("text", text, kwargs))

    async def reply_html(self, text, **kwargs):
        self.replies.append(("html", text, kwargs))


class FakeUpdate:
    def __init__(self, chat_id, chat_type="private", text=""):
        self.effective_chat = FakeChat(chat_id, chat_type)
        self.effective_message = FakeMessage(text)


class FakeApplication:
    def __init__(self, store=None):
        self.bot_data = {"user_store": store} if store is not None else {}


class FakeContext:
    def __init__(self, store=None):
        self.application = FakeApplication(store)


@pytest.mark.asyncio
async def test_remember_chat_id_uses_effective_chat_id():
    store = FakeStore()
    update = FakeUpdate(98765)

    created = await remember_chat_id(update, store)

    assert created is True
    assert store.chat_ids == [98765]


@pytest.mark.asyncio
async def test_remember_chat_id_skips_non_private_chats():
    store = FakeStore()
    update = FakeUpdate(-100123, chat_type="channel")

    created = await remember_chat_id(update, store)

    assert created is False
    assert store.chat_ids == []


@pytest.mark.asyncio
async def test_free_text_search_ignores_channel_updates_without_replying():
    store = FakeStore()
    update = FakeUpdate(-100123, chat_type="channel", text="ubuntu")
    context = FakeContext(store)

    await free_text_search(update, context)

    assert store.chat_ids == []
    assert update.effective_message.replies == []
