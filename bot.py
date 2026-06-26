#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Free Fire Auto-Like Telegram Bot (v3)
=====================================

Ei bot Free Fire player der jonno LIKE pathay.

⚠️ IMPORTANT / GURUTTOPURNO:
    Garena er kono OFFICIAL "like" API nai. Ei bot community/public like
    service er upor depend kore — ar SHOB free public API maje maje BONDHO
    hoye jay ba rate-limit kore. Tai 100% guarantee nai.

    >>> NEW in v3: Ekta DEFAULT public like API already boshano ache. <<<
    Tumi shudhu BOT_TOKEN diye chalalei bot try korbe. LIKE_API_URL na dile
    bot niche deya DEFAULT_LIKE_ENDPOINTS list er protita try kore (fallback).

    Jodi default API bondho hoye jay -> .env e tomar nijer LIKE_API_URL
    boshao (ekta kaj kora endpoint khuje niye). Format:
        LIKE_API_URL=https://your-host/like   (uid & region query param ney)

    Bot region = "bd" e call kore ebong result dekhay:
        likes before, likes added, likes after.

Features:
    /like bd <uid>      -> ek baar manual like pathao
    /autolike bd <uid>  -> protidin auto-like er jonno UID register koro
    /stop <uid>         -> auto-like bondho koro
    /list               -> tomar register kora UID gula dekho
    Daily scheduler     -> protidin automatic ভাবে DAILY_LIKES like pathay

Storage: SQLite (likebot.db) -> restart korleo data thake.
Scheduler: APScheduler (AsyncIOScheduler).
"""

import os
import logging
import sqlite3
import datetime as dt
from contextlib import closing

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# ---------------------------------------------------------------------------
# Configuration (sob kichu .env / environment variable theke ase)
# ---------------------------------------------------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
LIKE_API_URL = os.environ.get("LIKE_API_URL", "").strip()
LIKE_API_KEY = os.environ.get("LIKE_API_KEY", "").strip()

# ---------------------------------------------------------------------------
# DEFAULT public like endpoints (v3)
# ---------------------------------------------------------------------------
# Ei list er endpoint gula community-hosted free Free Fire like API.
# Jodi user LIKE_API_URL na dey, bot ei list er protita endpoint try korbe
# (jeta age kaj korbe seta use korbe). {uid} ar {region} placeholder replace hoy.
#
# ⚠️ BAASTOBOTA / REALITY: ei free endpoint gula prai bondho/down thake ba
#    rate-limit kore. Tai GUARANTEE NAI. Bondho hole .env e tomar nijer
#    LIKE_API_URL boshao. Notun endpoint khujte GitHub e "freefire like api"
#    search koro (jemon jinix6/free-ff-api style /api/v1 host).
#
# Format: GET, JSON response with likes before/after. {uid}/{region} replace hoy.
DEFAULT_LIKE_ENDPOINTS = [
    "https://free-ff-api-src-5plp.onrender.com/api/v1/like?region={region}&uid={uid}",
    "https://freefire-info-site.vercel.app/like?region={region}&uid={uid}",
    "https://ff-like-api.vercel.app/api/like?uid={uid}&region={region}",
]

# Protidin koto like pathabe (configurable). Default 200.
DAILY_LIKES = int(os.environ.get("DAILY_LIKES", "200"))

# Region fixed "bd" (requirement onujayi), kintu env diye change kora jay.
DEFAULT_REGION = os.environ.get("REGION", "bd").strip().lower()

# Daily scheduler koto somoy cholbe (24h format, server timezone)। Default raat 12:05.
SCHEDULE_HOUR = int(os.environ.get("SCHEDULE_HOUR", "0"))
SCHEDULE_MINUTE = int(os.environ.get("SCHEDULE_MINUTE", "5"))

# HTTP request timeout (seconds)
HTTP_TIMEOUT = float(os.environ.get("HTTP_TIMEOUT", "30"))

DB_PATH = os.environ.get("DB_PATH", "likebot.db")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("freefire-like-bot")


# ---------------------------------------------------------------------------
# Database layer (SQLite) - persistent storage
# ---------------------------------------------------------------------------
def db_init() -> None:
    """Table banai jodi na thake."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS autolike (
                uid         TEXT NOT NULL,
                region      TEXT NOT NULL DEFAULT 'bd',
                chat_id     INTEGER NOT NULL,
                added_at    TEXT NOT NULL,
                last_run    TEXT,
                PRIMARY KEY (uid, region)
            )
            """
        )
        conn.commit()


def db_add(uid: str, region: str, chat_id: int) -> bool:
    """UID register koro. Already thakle False."""
    now = dt.datetime.utcnow().isoformat()
    with closing(sqlite3.connect(DB_PATH)) as conn:
        try:
            conn.execute(
                "INSERT INTO autolike (uid, region, chat_id, added_at) VALUES (?, ?, ?, ?)",
                (uid, region, chat_id, now),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def db_remove(uid: str) -> int:
    """UID delete koro (sob region). Koto row delete holo return kore."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.execute("DELETE FROM autolike WHERE uid = ?", (uid,))
        conn.commit()
        return cur.rowcount


def db_list(chat_id: int):
    """Ei chat er register kora UID gula."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.execute(
            "SELECT uid, region, added_at, last_run FROM autolike WHERE chat_id = ? ORDER BY added_at",
            (chat_id,),
        )
        return cur.fetchall()


def db_all():
    """Sob register kora UID (scheduler er jonno)."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.execute("SELECT uid, region, chat_id FROM autolike")
        return cur.fetchall()


def db_mark_run(uid: str, region: str) -> None:
    now = dt.datetime.utcnow().isoformat()
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            "UPDATE autolike SET last_run = ? WHERE uid = ? AND region = ?",
            (now, uid, region),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Like API caller (PLUGGABLE - tomar nijer API)
# ---------------------------------------------------------------------------
def _parse_like_response(data) -> dict:
    """
    API response (dict) theke likes before/added/after ber kore.
    Onek free API alada field name use kore - tai onek variation detect kori.
    Nested object (jemon {"LikeInfo": {...}}) o handle kore.
    """
    # Jodi response er bhitore nested dict thake, seta o merge kore dei
    flat = {}
    if isinstance(data, dict):
        for k, v in data.items():
            flat[k] = v
            if isinstance(v, dict):
                for k2, v2 in v.items():
                    flat.setdefault(k2, v2)

    def pick(*keys):
        for k in keys:
            for fk in flat:
                if fk.lower() == k.lower() and flat[fk] is not None:
                    try:
                        return int(flat[fk])
                    except (ValueError, TypeError):
                        return flat[fk]
        return None

    before = pick("likes_before", "before", "LikesbeforeCommand", "before_like",
                  "PreLikes", "likesbefore", "Likes_before", "old_likes")
    after = pick("likes_after", "after", "LikesafterCommand", "after_like",
                 "AfterLikes", "likesafter", "Likes_after", "new_likes", "likes")
    added = pick("likes_added", "added", "LikesGivenByAPI", "likes_given",
                 "LikesGiven", "given", "added_likes")

    if added is None and isinstance(before, int) and isinstance(after, int):
        added = after - before

    return {"before": before, "added": added, "after": after}


async def _try_one_endpoint(client, url: str, uid: str, region: str,
                            amount: int | None) -> dict:
    """Ekta single endpoint ke call kore. URL e {uid}/{region} placeholder thakle
    replace kore, na thakle query param hisebe pathai."""
    headers = {"User-Agent": "Mozilla/5.0 (freefire-like-bot)"}
    if LIKE_API_KEY:
        headers["Authorization"] = f"Bearer {LIKE_API_KEY}"

    if "{uid}" in url or "{region}" in url:
        # Template style endpoint (default list)
        final_url = url.replace("{uid}", uid).replace("{region}", region)
        params = {}
        if LIKE_API_KEY:
            params["key"] = LIKE_API_KEY
    else:
        # User-provided plain endpoint -> query param diye pathai
        final_url = url
        params = {"uid": uid, "region": region}
        if LIKE_API_KEY:
            params["key"] = LIKE_API_KEY
        if amount is not None:
            params["amount"] = str(amount)

    resp = await client.get(final_url, params=params, headers=headers)
    resp.raise_for_status()
    try:
        data = resp.json()
    except Exception:
        return {"ok": True, "before": None, "added": None, "after": None,
                "raw": resp.text, "error": None, "endpoint": final_url}

    parsed = _parse_like_response(data)
    return {"ok": True, "raw": data, "error": None, "endpoint": final_url, **parsed}


async def call_like_api(uid: str, region: str, amount: int | None = None) -> dict:
    """
    Free Fire like API ke call kore.

    Priority:
        1. Jodi user LIKE_API_URL diye thake -> shudhu seta use kore.
        2. Na dile -> DEFAULT_LIKE_ENDPOINTS list er protita try kore
           (prothom jeta kaj kore seta).

    Return: {"ok": bool, "before": int|None, "added": int|None,
             "after": int|None, "raw": <api response>, "error": str|None}
    """
    # Kon endpoint gula try korbo, ti list banai
    if LIKE_API_URL:
        endpoints = [LIKE_API_URL]
    else:
        endpoints = list(DEFAULT_LIKE_ENDPOINTS)

    errors = []
    last_ok = None
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
        for url in endpoints:
            try:
                result = await _try_one_endpoint(client, url, uid, region, amount)
                # Jodi API success kintu kono like data nai, tobu valid -
                # kintu fallback list e thakle porer ta o try kori (better data)
                if result["ok"] and (result.get("after") is not None
                                     or result.get("added") is not None
                                     or len(endpoints) == 1):
                    return result
                # data nai -> ei OK result mone rakhi, shesh e fallback hisebe debo
                errors.append(f"{url.split('?')[0]}: response e like data nai")
                last_ok = result
            except httpx.HTTPStatusError as e:
                errors.append(f"{url.split('?')[0]}: HTTP {e.response.status_code}")
            except Exception as e:
                errors.append(f"{url.split('?')[0]}: {type(e).__name__}")

    # Jodi kono endpoint OK chilo kintu data chilo na -> oita-i dei
    if last_ok is not None:
        return last_ok

    return {
        "ok": False,
        "error": ("Kono like API kaj korlo na (sob down/rate-limited). "
                  ".env e tomar nijer LIKE_API_URL boshao.\n• " + "\n• ".join(errors[:5])),
        "before": None, "added": None, "after": None, "raw": None,
    }


def format_result(uid: str, region: str, result: dict) -> str:
    """Result ke sundor message banai."""
    if not result["ok"]:
        return (
            f"❌ <b>Like fail</b>\n"
            f"UID: <code>{uid}</code> (region: {region})\n"
            f"Reason: {result['error']}"
        )

    before = result["before"]
    added = result["added"]
    after = result["after"]

    lines = [
        f"✅ <b>Like sent!</b>",
        f"🎮 UID: <code>{uid}</code>  |  🌍 Region: <b>{region}</b>",
    ]
    if before is not None:
        lines.append(f"👍 Likes before: <b>{before}</b>")
    if added is not None:
        lines.append(f"➕ Likes added: <b>{added}</b>")
    if after is not None:
        lines.append(f"🏆 Likes after: <b>{after}</b>")
    if before is None and after is None:
        lines.append(f"ℹ️ API response: <code>{str(result['raw'])[:300]}</code>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = (
        "🔥 <b>Free Fire Auto-Like Bot</b> 🔥\n\n"
        "<b>Commands:</b>\n"
        "• <code>/like bd &lt;uid&gt;</code> — ekbar manual like pathao\n"
        f"• <code>/autolike bd &lt;uid&gt;</code> — protidin auto-like ({DAILY_LIKES}/day) register koro\n"
        "• <code>/stop &lt;uid&gt;</code> — auto-like bondho koro\n"
        "• <code>/list</code> — register kora UID dekho\n\n"
        "⚠️ <i>Garena er official like API nai. Ei bot ekta DEFAULT public "
        "like API use kore (free, tai maje maje down thakte pare). Bondho hole "
        ".env e nijer LIKE_API_URL boshao.</i>"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


def _parse_region_uid(args, default_region: str):
    """
    Support korе:
        /like bd 12345     -> region=bd, uid=12345
        /like 12345        -> region=default, uid=12345
        /autolike bd 12345 -> region=bd, uid=12345
    """
    if not args:
        return None, None
    if len(args) >= 2:
        return args[0].lower(), args[1]
    return default_region, args[0]


async def cmd_like(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    region, uid = _parse_region_uid(context.args, DEFAULT_REGION)
    if not uid or not uid.isdigit():
        await update.message.reply_text(
            "❌ Use: <code>/like bd &lt;uid&gt;</code>\nExample: <code>/like bd 123456789</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    wait = await update.message.reply_text(f"⏳ Liking UID <code>{uid}</code>...", parse_mode=ParseMode.HTML)
    result = await call_like_api(uid, region)
    await wait.edit_text(format_result(uid, region, result), parse_mode=ParseMode.HTML)


async def cmd_autolike(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    region, uid = _parse_region_uid(context.args, DEFAULT_REGION)
    if not uid or not uid.isdigit():
        await update.message.reply_text(
            "❌ Use: <code>/autolike bd &lt;uid&gt;</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    added = db_add(uid, region, update.effective_chat.id)
    if added:
        await update.message.reply_text(
            f"✅ <b>Auto-like ON</b>\nUID <code>{uid}</code> (region {region}) "
            f"register holo. Protidin <b>{DAILY_LIKES}</b> like pabe.\n"
            f"⏰ Next run: prottek din {SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d} (server time).",
            parse_mode=ParseMode.HTML,
        )
        # Sathe sathe ekbar like diye dei (instant feedback)
        result = await call_like_api(uid, region, DAILY_LIKES)
        db_mark_run(uid, region)
        await update.message.reply_text(format_result(uid, region, result), parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(
            f"ℹ️ UID <code>{uid}</code> already register kora ache.",
            parse_mode=ParseMode.HTML,
        )


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            "❌ Use: <code>/stop &lt;uid&gt;</code>", parse_mode=ParseMode.HTML
        )
        return
    uid = context.args[0]
    n = db_remove(uid)
    if n:
        await update.message.reply_text(
            f"🛑 UID <code>{uid}</code> er auto-like bondho holo.", parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            f"ℹ️ UID <code>{uid}</code> register kora chilo na.", parse_mode=ParseMode.HTML
        )


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = db_list(update.effective_chat.id)
    if not rows:
        await update.message.reply_text(
            "📭 Kono UID register kora nai.\n<code>/autolike bd &lt;uid&gt;</code> diye add koro.",
            parse_mode=ParseMode.HTML,
        )
        return
    lines = [f"📋 <b>Registered UIDs</b> (daily {DAILY_LIKES} likes):"]
    for uid, region, added_at, last_run in rows:
        lr = last_run.split("T")[0] if last_run else "never"
        lines.append(f"• <code>{uid}</code> ({region}) — last run: {lr}")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


# ---------------------------------------------------------------------------
# Daily scheduler job
# ---------------------------------------------------------------------------
async def daily_autolike_job(app: Application) -> None:
    """Protidin ek baar chole - sob register kora UID ke like pathay."""
    rows = db_all()
    logger.info("Daily auto-like job shuru. Total UID: %d", len(rows))
    for uid, region, chat_id in rows:
        try:
            result = await call_like_api(uid, region, DAILY_LIKES)
            db_mark_run(uid, region)
            text = "🤖 <b>Daily auto-like</b>\n" + format_result(uid, region, result)
            await app.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.exception("Auto-like fail for UID %s: %s", uid, e)


# ---------------------------------------------------------------------------
# App bootstrap
# ---------------------------------------------------------------------------
def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN set kora nai! .env e BOT_TOKEN dao.")

    db_init()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("like", cmd_like))
    app.add_handler(CommandHandler("autolike", cmd_autolike))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("list", cmd_list))

    # --- APScheduler: protidin ekbar ---
    scheduler = AsyncIOScheduler(timezone=os.environ.get("TZ", "UTC"))
    scheduler.add_job(
        daily_autolike_job,
        trigger=CronTrigger(hour=SCHEDULE_HOUR, minute=SCHEDULE_MINUTE),
        args=[app],
        id="daily_autolike",
        replace_existing=True,
    )

    async def _post_init(application: Application) -> None:
        scheduler.start()
        logger.info(
            "Scheduler started: protidin %02d:%02d e %d like/UID.",
            SCHEDULE_HOUR, SCHEDULE_MINUTE, DAILY_LIKES,
        )

    app.post_init = _post_init

    logger.info("Bot cholche... (Ctrl+C diye bondho koro)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
