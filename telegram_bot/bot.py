"""
Telegram bot for PokeCard price scraping.

Commands:
    /start          - Welcome message
    /scrape [mode]  - Run scrape (both | fastbuy | onechome)
    /status         - Check current scrape status
    /results        - Show latest price comparison
    /csv            - Send CSV report file
"""

import logging
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from kaitori_scraper.config.collection import get_collection_by_ids
from kaitori_scraper.scrapers.fastbuy_scraper import FastbuyScraper
from kaitori_scraper.scrapers.onechome_scraper import OneChomeScraper
from kaitori_scraper.output.comparator import compare_results
from kaitori_scraper.output.report import generate_text_report, generate_csv_report

logger = logging.getLogger(__name__)

# ── In-memory state (per-bot instance) ──

_running = False
_last_text: str | None = None
_last_csv: str | None = None
_last_time: datetime | None = None


def create_bot(token: str) -> Application:
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", _cmd_start))
    app.add_handler(CommandHandler("scrape", _cmd_scrape))
    app.add_handler(CommandHandler("status", _cmd_status))
    app.add_handler(CommandHandler("results", _cmd_results))
    app.add_handler(CommandHandler("csv", _cmd_csv))
    return app


# ── Command handlers ──


async def _cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🃏 *PokeCard 買取スクレイパー*\n\n"
        "コマンド一覧:\n"
        "/scrape — 両方のサイトを爬取\n"
        "/scrape fastbuy — Fastbuy のみ\n"
        "/scrape onechome — 1-chome のみ\n"
        "/status — 実行状態を確認\n"
        "/results — 最新結果を表示\n"
        "/csv — CSV ファイルを送信",
        parse_mode="Markdown",
    )


async def _cmd_scrape(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    global _running

    if _running:
        await update.message.reply_text("⏳ 爬取が既に実行中です。/status で確認してください。")
        return

    args = ctx.args
    mode = args[0] if args else "both"
    if mode not in ("both", "fastbuy", "onechome"):
        await update.message.reply_text("❌ モード: both / fastbuy / onechome")
        return

    _running = True
    msg = await update.message.reply_text(f"🔄 爬取開始 (mode: {mode})...")

    try:
        await _run_scrape(mode, msg)
    finally:
        _running = False


async def _cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if _running:
        await update.message.reply_text("⏳ 爬取実行中...")
    elif _last_time:
        await update.message.reply_text(
            f"✅ 最終実行: {_last_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            "/results で結果を表示"
        )
    else:
        await update.message.reply_text("💤 まだ爬取を実行していません。/scrape で開始")


async def _cmd_results(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _last_text:
        await update.message.reply_text("❌ 結果がありません。先に /scrape を実行してください。")
        return

    # Telegram message limit is 4096 chars; split if needed
    text = _last_text
    while text:
        chunk, text = text[:4000], text[4000:]
        await update.message.reply_text(f"```\n{chunk}\n```", parse_mode="Markdown")


async def _cmd_csv(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _last_csv:
        await update.message.reply_text("❌ 結果がありません。先に /scrape を実行してください。")
        return

    ts = _last_time.strftime("%Y%m%d_%H%M%S") if _last_time else "report"
    await update.message.reply_document(
        document=_last_csv.encode("utf-8-sig"),
        filename=f"price_report_{ts}.csv",
    )


# ── Scraping logic ──


async def _run_scrape(mode: str, msg) -> None:
    global _last_text, _last_csv, _last_time

    items = get_collection_by_ids(None)
    timestamp = datetime.now()
    fastbuy_results = []
    onechome_results = []

    try:
        if mode in ("fastbuy", "both"):
            await msg.edit_text("🔄 Scraping fastbuy.jp...")
            scraper = FastbuyScraper()
            fastbuy_results = await scraper.scrape(items)

        if mode in ("onechome", "both"):
            await msg.edit_text("🔄 Scraping 1-chome.com...")
            scraper = OneChomeScraper()
            onechome_results = await scraper.scrape(items)

        await msg.edit_text("🔄 Comparing results...")
        comparison = compare_results(items, fastbuy_results, onechome_results)

        _last_text = generate_text_report(comparison, timestamp)
        _last_csv = generate_csv_report(comparison, timestamp)
        _last_time = datetime.now()

        # Build summary
        lines = ["✅ *爬取完了!*\n"]
        for row in comparison:
            item = row.collection_item
            fb_price = ""
            oc_price = ""
            if row.fastbuy_match and row.fastbuy_match.product:
                p = row.fastbuy_match.product
                fb_price = f"¥{p.price_low:,}"
            if row.onechome_match and row.onechome_match.product:
                p = row.onechome_match.product
                oc_price = f"¥{p.price_low:,}"
            rec = ""
            if row.recommendation:
                rec = f" 👉{row.recommendation}"
            lines.append(
                f"*{item.name_jp}* x{item.quantity}\n"
                f"  FB: {fb_price or '--'}  |  1C: {oc_price or '--'}{rec}"
            )

        summary = "\n".join(lines)
        if len(summary) > 4000:
            summary = summary[:3990] + "\n..."
        summary += "\n\n/results で詳細 | /csv でファイル"

        await msg.edit_text(summary, parse_mode="Markdown")

    except Exception as e:
        logger.exception("Scrape failed")
        await msg.edit_text(f"❌ エラー: {e}")
