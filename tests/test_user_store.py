from user_store import MongoUserStore, NullUserStore, build_user_document


class FakeUpdateResult:
    def __init__(self, upserted_id=None):
        self.upserted_id = upserted_id


class FakeCollection:
    def __init__(self, result):
        self.result = result
        self.indexes = []
        self.operations = []

    def create_index(self, keys, unique=False):
        self.indexes.append((keys, unique))

    def update_one(self, query, update, upsert=False):
        self.operations.append((query, update, upsert))
        return self.result


def test_build_user_document_uses_legacy_chat_id_shape():
    assert build_user_document(12345) == {"chat_id": 12345}


def test_mongo_user_store_upserts_chat_id_once_shape():
    collection = FakeCollection(FakeUpdateResult(upserted_id="new-id"))
    store = MongoUserStore(collection)

    created = store.ensure_user(12345)

    assert created is True
    assert collection.indexes == [([("chat_id", 1)], True)]
    assert collection.operations == [
        ({"chat_id": 12345}, {"$setOnInsert": {"chat_id": 12345}}, True)
    ]


def test_mongo_user_store_returns_false_when_existing_user_skipped():
    collection = FakeCollection(FakeUpdateResult(upserted_id=None))
    store = MongoUserStore(collection)

    assert store.ensure_user(12345) is False


def test_null_user_store_is_safe_when_mongodb_not_configured():
    assert NullUserStore().ensure_user(12345) is False
