from __future__ import annotations

import logging
import os
from typing import Protocol

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

LOG = logging.getLogger(__name__)


class UserStore(Protocol):
    def ensure_user(self, chat_id: int) -> bool:
        """Ensure a Telegram chat id exists. Return True only when inserted."""
        ...


def build_user_document(chat_id: int) -> dict[str, int]:
    # Preserve the legacy collection shape: existing docs only contain chat_id.
    return {"chat_id": int(chat_id)}


class NullUserStore:
    def ensure_user(self, chat_id: int) -> bool:
        return False


class MongoUserStore:
    def __init__(self, collection: Collection):
        self.collection = collection
        self.collection.create_index([("chat_id", 1)], unique=True)

    def ensure_user(self, chat_id: int) -> bool:
        doc = build_user_document(chat_id)
        result = self.collection.update_one(
            {"chat_id": doc["chat_id"]},
            {"$setOnInsert": doc},
            upsert=True,
        )
        return result.upserted_id is not None


def build_user_store_from_env() -> UserStore:
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        LOG.warning("MONGODB_URI not configured; user chat ids will not be persisted")
        return NullUserStore()

    database = os.environ.get("MONGODB_DATABASE", "telegram_torrent")
    collection_name = os.environ.get("MONGODB_USERS_COLLECTION", "users")
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=10000)
        client.admin.command("ping")
        return MongoUserStore(client[database][collection_name])
    except PyMongoError:
        LOG.exception("MongoDB user store unavailable; continuing without persistence")
        return NullUserStore()
