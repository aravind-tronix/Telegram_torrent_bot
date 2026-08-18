from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from prowlarr_client import ProwlarrClient, format_result

LOG = logging.getLogger(__name__)


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


def result_limit() -> int:
    try:
        return max(1, min(20, int(os.environ.get("BOT_RESULT_LIMIT", "10"))))
    except ValueError:
        return 10


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "Send /search <query> to search configured torrent indexers.\n"
        "Example: /search ubuntu\n\n"
        "Sources are served through local Prowlarr, not direct site scraping."
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    client: ProwlarrClient = context.application.bot_data["prowlarr"]
    try:
        results = await asyncio.to_thread(client.search, "ubuntu", 3)
        await update.effective_message.reply_text(
            f"Prowlarr OK. Test search returned {len(results)} sample results."
        )
    except Exception as exc:  # noqa: BLE001 - user-facing bot status
        LOG.exception("status check failed")
        await update.effective_message.reply_text(f"Prowlarr check failed: {exc}")


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args).strip()
    if not query:
        await update.effective_message.reply_text("Usage: /search <movie/app/software/query>")
        return
    await run_search(update, context, query)


async def free_text_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.effective_message.text or "").strip()
    if not text:
        return
    await run_search(update, context, text)


async def run_search(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str) -> None:
    client: ProwlarrClient = context.application.bot_data["prowlarr"]
    notice = await update.effective_message.reply_text(f"Searching Prowlarr for: {query}")
    try:
        results = await asyncio.to_thread(client.search, query, result_limit())
    except Exception as exc:  # noqa: BLE001 - keep bot alive and report failure
        LOG.exception("search failed for %r", query)
        await notice.edit_text(f"Search failed: {exc}")
        return

    if not results:
        await notice.edit_text("No results found from configured indexers.")
        return

    await notice.edit_text(f"Found {len(results)} results. Sending...")
    for idx, result in enumerate(results, start=1):
        await update.effective_message.reply_html(
            format_result(result, idx),
            disable_web_page_preview=True,
        )


def build_app() -> object:
    load_env_file(os.environ.get("BOT_ENV_FILE", "/root/.config/telegram-torrent-bot/bot.env"))
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")

    application = ApplicationBuilder().token(token).build()
    application.bot_data["prowlarr"] = ProwlarrClient()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, free_text_search))
    return application


def main() -> None:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    # httpx logs Telegram API URLs; keep tokens out of journald.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    app = build_app()
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
