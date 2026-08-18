import pytest

from app import remember_chat_id


class FakeStore:
    def __init__(self):
        self.chat_ids = []

    def ensure_user(self, chat_id):
        self.chat_ids.append(chat_id)
        return True


class FakeChat:
    def __init__(self, chat_id):
        self.id = chat_id


class FakeUpdate:
    def __init__(self, chat_id):
        self.effective_chat = FakeChat(chat_id)


@pytest.mark.asyncio
async def test_remember_chat_id_uses_effective_chat_id():
    store = FakeStore()
    update = FakeUpdate(98765)

    created = await remember_chat_id(update, store)

    assert created is True
    assert store.chat_ids == [98765]
