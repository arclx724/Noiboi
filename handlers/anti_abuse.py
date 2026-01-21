import re
import aiohttp
import asyncio

from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MessageEntity
)

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


    # ================= AI CHECK =================

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
            return await message.reply("❌ Only admins can use this.")

        if len(message.command) > 1:
            arg = message.command[1].lower()
            new_status = arg in ("on", "enable", "yes")
        else:
            current = await db.is_abuse_enabled(message.chat.id)
            new_status = not current

        await db.set_abuse_status(message.chat.id, new_status)
        state = "Enabled ✅" if new_status else "Disabled ❌"
        await message.reply(f"🛡 Abuse protection is now {state}")


    # ================= ABUSE WATCHER =================

@app.on_message(filters.text & filters.group & ~filters.bot, group=10)
async def abuse_watcher(client, message):

    # ---------- SAFETY ----------
    if not message.from_user:
        return

    # ---------- CHECKS ----------
    if not await db.is_abuse_enabled(message.chat.id):
        return

    if await is_admin(message.chat.id, message.from_user.id):
        return

    if await db.is_user_whitelisted(message.chat.id, message.from_user.id):
        return

    text = message.text
    detected = False

    # ---------- LOCAL WORD CHECK ----------
    for word in ABUSIVE_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE):
            detected = True
            break

    # ---------- AI CHECK ----------
    if not detected and OPENROUTER_API_KEY:
        detected = await check_toxicity_ai(text)

    if not detected:
        return

    try:
        # delete abusive msg
        await message.delete()

        user = message.from_user
        name = user.first_name or "User"

        # ❗ NO HTML, NO ENTITIES, NO MENTION
        warn_text = (
            f"🚫 Hey {name}, your message was removed.\n\n"
            f"🔍 Censored:\n██████\n\n"
            f"⚠️ Please keep the chat respectful."
        )

        # ❗ IMPORTANT FIX — send_message + parse_mode=None
        sent = await client.send_message(
            chat_id=message.chat.id,
            text=warn_text,
            parse_mode=None,
            disable_web_page_preview=True
        )

        await asyncio.sleep(60)
        await sent.delete()

    except Exception as e:
        print("Abuse filter error:", e)

        # -------- AI CHECK --------
        if not detected and OPENROUTER_API_KEY:
            detected = await check_toxicity_ai(text)

        if not detected:
            return

        try:
            await message.delete()

            user = message.from_user
            name = user.first_name or "User"

            base_text = (
                "🚫 Hey " + name + ", your message was removed.\n\n"
                "🔍 Censored:\n"
                "████████\n\n"
                "⚠️ Please be respectful."
            )

            # Mention entity (NO HTML / NO MARKDOWN)
            entities = [
                MessageEntity(
                    type="text_mention",
                    offset=5,              # "🚫 Hey " = 5 chars
                    length=len(name),
                    user=user
                )
            ]

            buttons = InlineKeyboardMarkup(
                [[InlineKeyboardButton("📢 Updates", url=f"https://t.me/{BOT_USERNAME}")]]
            )

            sent = await message.reply(
                base_text,
                entities=entities,
                reply_markup=buttons,
                disable_web_page_preview=True
            )

            await asyncio.sleep(60)
            await sent.delete()

        except Exception as e:
            print("Abuse filter error:", e)
