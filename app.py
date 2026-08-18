from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from telegram import BotCommand, ReplyKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import AIORateLimiter, Application, ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from prowlarr_client import ProwlarrClient, TorrentResult, format_result

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


def message_interval_seconds() -> float:
    try:
        interval = float(os.environ.get("BOT_MESSAGE_INTERVAL_SECONDS", "1.1"))
    except ValueError:
        interval = 1.1
    return max(0.5, min(5.0, interval))


def admin_contact() -> str:
    return os.environ.get("BOT_ADMIN_CONTACT", "Contact admin @aravind_at_telegram")


def menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            ["Search"],
            ["Read me"],
            ["Privacy Policy", "Terms"],
        ],
        resize_keyboard=True,
    )


def info_response(label: str) -> str:
    contact = admin_contact()
    messages = {
        "Read me": (
            "Welcome to Torrent Bot. Here are some clarifications\n\n"
            "<b>Do i need a vpn to use this bot?</b>\n"
            "No. You do not require a vpn to search using this bot.\n\n"
            "<b>Why are some torrent links not opening?</b>\n"
            "Some ISPs may block torrent sites or torrent files. If a link does not open, "
            "try a VPN or another client.\n\n"
            f"{contact}"
        ),
        "Privacy Policy": (
            "Welcome to Torrent Bot. Our privacy policy\n\n"
            "We don't store your data or search queries in the bot code. "
            "Searches are sent to the local Prowlarr service configured by the bot owner.\n\n"
            f"{contact}"
        ),
        "Terms": (
            "Welcome to Torrent Bot. Terms of use\n\n"
            "We are not responsible for the contents you see, open, or download using this bot. "
            "Use it only where you have the legal right to access the content.\n\n"
            f"{contact}"
        ),
    }
    return messages[label]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "Hi! Send /search <query> or choose from the menu below.\n"
        "Example: /search ubuntu\n\n"
        "Sources are served through local Prowlarr, not direct site scraping.",
        reply_markup=menu_keyboard(),
    )


async def readme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_html(info_response("Read me"), reply_markup=menu_keyboard())


async def privacy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_html(info_response("Privacy Policy"), reply_markup=menu_keyboard())


async def terms(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_html(info_response("Terms"), reply_markup=menu_keyboard())


async def configure_bot_commands(application: Application) -> None:
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Show menu"),
            BotCommand("search", "Search torrents"),
            BotCommand("status", "Check Prowlarr status"),
            BotCommand("readme", "How to use this bot"),
            BotCommand("privacy", "Privacy policy"),
            BotCommand("terms", "Terms of use"),
        ]
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
    if text in {"Read me", "Privacy Policy", "Terms"}:
        await update.effective_message.reply_html(info_response(text), reply_markup=menu_keyboard())
        return
    if text == "Search":
        await update.effective_message.reply_text("Type /search <query> or just send the search text.", reply_markup=menu_keyboard())
        return
    await run_search(update, context, text)


async def send_results(
    update: Update,
    results: list[TorrentResult],
    delay_seconds: float | None = None,
    sleeper=asyncio.sleep,
) -> None:
    delay = message_interval_seconds() if delay_seconds is None else delay_seconds
    for idx, result in enumerate(results, start=1):
        await update.effective_message.reply_html(
            format_result(result, idx),
            disable_web_page_preview=True,
        )
        if idx < len(results):
            await sleeper(delay)


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

    await notice.edit_text(f"Found {len(results)} results. Sending with pacing...")
    await send_results(update, results)


def build_app() -> Application:
    load_env_file(os.environ.get("BOT_ENV_FILE", "/root/.config/telegram-torrent-bot/bot.env"))
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")

    application = (
        ApplicationBuilder()
        .token(token)
        .rate_limiter(AIORateLimiter())
        .post_init(configure_bot_commands)
        .build()
    )
    application.bot_data["prowlarr"] = ProwlarrClient()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("readme", readme))
    application.add_handler(CommandHandler("privacy", privacy))
    application.add_handler(CommandHandler("terms", terms))
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
