#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable, Iterable

from pymongo import MongoClient
from telegram import Bot
from telegram.error import Forbidden, RetryAfter

LOG = logging.getLogger(__name__)
DEFAULT_MESSAGE = (
    "✅ Torrent Bot is back online!\n\n"
    "Please restart the bot with /start to refresh the menu.\n\n"
    "How to use:\n"
    "• Tap /start\n"
    "• Use /search movie name or just send the movie/app/software name\n"
    "• Use Read me, Privacy Policy, and Terms from the menu\n\n"
    "If you like the bot, share it with your friends:\n"
    "https://t.me/Torrent_link_bot"
)


@dataclass(frozen=True)
class BroadcastStats:
    total: int
    sent: int
    failed: int
    skipped: int


def load_env_file(path: str | Path) -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def iter_chat_ids(collection) -> Iterable[int]:
    seen: set[int] = set()
    for doc in collection.find({"chat_id": {"$exists": True}}, {"_id": 0, "chat_id": 1}):
        try:
            chat_id = int(doc.get("chat_id"))
        except (TypeError, ValueError):
            continue
        if chat_id in seen:
            continue
        seen.add(chat_id)
        yield chat_id


def get_users_collection():
    uri = os.environ["MONGODB_URI"]
    database = os.environ.get("MONGODB_DATABASE", "telegram_torrent")
    collection = os.environ.get("MONGODB_USERS_COLLECTION", "users")
    client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    client.admin.command("ping")
    return client[database][collection]


async def send_one(bot: Bot, chat_id: int, message: str) -> bool:
    try:
        await bot.send_message(chat_id=chat_id, text=message, disable_web_page_preview=True)
        return True
    except RetryAfter as exc:
        wait_for = int(getattr(exc, "retry_after", 5)) + 1
        LOG.warning("Telegram throttle for chat_id=%s; sleeping %ss", chat_id, wait_for)
        await asyncio.sleep(wait_for)
        await bot.send_message(chat_id=chat_id, text=message, disable_web_page_preview=True)
        return True
    except Forbidden:
        LOG.info("Skipping chat_id=%s; user blocked bot or chat unavailable", chat_id)
        return False
    except Exception:  # noqa: BLE001 - keep one bad recipient from aborting the broadcast
        LOG.exception("Failed to send to chat_id=%s", chat_id)
        return False


async def run_broadcast(
    chat_ids: list[int],
    bot,
    message: str,
    execute: bool,
    delay_seconds: float,
    collection=None,
    sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> BroadcastStats:
    sent = failed = skipped = 0
    total = len(chat_ids)
    for idx, chat_id in enumerate(chat_ids, start=1):
        if not execute:
            skipped += 1
        else:
            ok = await send_one(bot, chat_id, message)
            if ok:
                sent += 1
            else:
                failed += 1
                if collection is not None:
                    try:
                        collection.delete_one({"chat_id": chat_id})
                        LOG.info("Deleted unreachable chat_id=%s from MongoDB", chat_id)
                    except Exception:  # noqa: BLE001 - deletion failure should not abort remaining sends
                        LOG.exception("Failed to delete unreachable chat_id=%s from MongoDB", chat_id)
        if idx < total and delay_seconds > 0:
            await sleeper(delay_seconds)
    return BroadcastStats(total=total, sent=sent, failed=failed, skipped=skipped)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Broadcast an alive message to Telegram users stored in MongoDB.")
    parser.add_argument("--env-file", default="/root/.config/telegram-torrent-bot/bot.env")
    parser.add_argument("--message", default=DEFAULT_MESSAGE)
    parser.add_argument("--delay", type=float, default=float(os.environ.get("BOT_BROADCAST_INTERVAL_SECONDS", "1.2")))
    parser.add_argument("--limit", type=int, default=0, help="Limit number of users; 0 means all users.")
    parser.add_argument("--execute", action="store_true", help="Actually send messages. Without this, dry-run only.")
    return parser.parse_args()


async def async_main() -> int:
    args = parse_args()
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    load_env_file(args.env_file)

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")

    collection = get_users_collection()
    chat_ids = list(iter_chat_ids(collection))
    if args.limit > 0:
        chat_ids = chat_ids[: args.limit]

    print(f"mode={'EXECUTE' if args.execute else 'DRY_RUN'} users={len(chat_ids)} delay={args.delay}s")
    stats = await run_broadcast(
        chat_ids=chat_ids,
        bot=Bot(token),
        message=args.message,
        execute=args.execute,
        delay_seconds=args.delay,
        collection=collection,
    )
    print(f"total={stats.total} sent={stats.sent} failed={stats.failed} skipped={stats.skipped}")
    return 0 if stats.failed == 0 else 1


def main() -> None:
    raise SystemExit(asyncio.run(async_main()))


if __name__ == "__main__":
    main()
