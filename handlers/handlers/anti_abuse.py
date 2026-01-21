import re
import aiohttp
import asyncio
from html import escape

from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus, ParseMode
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import OPENROUTER_API_KEY, BOT_USERNAME
import db


# ================= ABUSIVE WORDS =================

ABUSIVE_WORDS = [
    "madarchod", "madharchod", "behenchod", "bhenchod", "mc", "bc", "bsdk",
    "bhosdike", "chutiya", "gandu", "lodu", "lauda", "lund", "lawda",
    "chut", "tatte", "gaand", "kamina", "harami", "kutte", "kutta",
    "saala", "saali", "randi", "fuck", "bitch", "asshole",
    "motherfucker", "dick", "tmkc", "mkc"
]


API_URL = "https://openrouter.ai/api/v1/chat/completions"


def register_abuse_handlers(app: Client):

    # ================= ADMIN CHECK =================

    async def is_admin(chat_id, user_id):
        try:
            member = await app.get_chat_member(chat_id, user_id)
            return member.status in (
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.OWNER
            )
        except:
            return False


    # ================= AI TOXICITY CHECK =================

    async def check_toxicity_ai(text: str) -> bool:
        if not text or not OPENROUTER_API_KEY:
            return False

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://telegram.org",
        }

        payload = {
            "model": "google/gemini-2.0-flash-exp:free",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Reply ONLY with YES if message contains "
                        "hate speech, severe abuse or extreme profanity. "
                        "Reply NO if safe."
                    )
                },
                {"role": "user", "content": text}
            ],
            "temperature": 0.1,
            "max_tokens": 5
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL, headers=headers, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        answer = data["choices"][0]["message"]["content"].strip().upper()
                        return answer == "YES"
        except:
            pass

        return False


    # ================= TOGGLE COMMAND =================

    @app.on_message(filters.command("abuse") & filters.group)
    async def toggle_abuse(_, message):
        if not await is_admin(message.chat.id, message.from_user.id):
            return await message.reply_text("❌ Only admins can use this.")

        if len(message.command) > 1:
            arg = message.command[1].lower()
            new_status = arg in ("on", "enable", "yes")
        else:
            current = await db.is_abuse_enabled(message.chat.id)
            new_status = not current

        await db.set_abuse_status(message.chat.id, new_status)
        state = "Enabled ✅" if new_status else "Disabled ❌"
        await message.reply_text(f"🛡 Abuse protection is now {state}")


    # ================= ABUSE WATCHER =================

    @app.on_message(filters.text & filters.group & ~filters.bot, group=10)
    async def abuse_watcher(_, message):

        # Check enabled
        if not await db.is_abuse_enabled(message.chat.id):
            return

        # Admin immune
        if await is_admin(message.chat.id, message.from_user.id):
            return

        # Whitelist
        if await db.is_user_whitelisted(message.chat.id, message.from_user.id):
            return

        text = message.text
        detected = False

        # -------- LOCAL CHECK --------
        for word in ABUSIVE_WORDS:
            pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
            if pattern.search(text):
                detected = True
                break

        # -------- AI CHECK --------
        if not detected and OPENROUTER_API_KEY:
            detected = await check_toxicity_ai(text)

        # -------- ACTION --------
        if not detected:
            return

        try:
            await message.delete()

            mention = message.from_user.mention_html()
            safe_text = escape(text)

            buttons = InlineKeyboardMarkup(
                [[InlineKeyboardButton("📢 Updates", url=f"https://t.me/{BOT_USERNAME}")]]
            )

            warning_text = (
                f"🚫 Hey {mention}, your message was removed.\n\n"
                f"🔍 <b>Censored:</b>\n"
                f"<spoiler>{safe_text}</spoiler>\n\n"
                f"⚠️ Please be respectful."
            )

            sent = await message.reply_html(
    warning_text,
    reply_markup=buttons,
    disable_web_page_preview=True
            )

            await asyncio.sleep(60)
            await sent.delete()

        except Exception as e:
            print("Abuse filter error:", e)
