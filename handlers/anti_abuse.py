import re
import asyncio
from pyrogram import filters
from pyrogram.types import Message

from db import db
from utils.admins import is_admin
from ai.toxicity import check_toxicity_ai
from config import OPENROUTER_API_KEY, ABUSIVE_WORDS


def register_abuse_handlers(app):

    @app.on_message(filters.text & filters.group & ~filters.bot, group=10)
    async def abuse_watcher(_, message: Message):

        if not message.from_user:
            return

        chat_id = message.chat.id
        user_id = message.from_user.id

        # Feature enabled?
        if not await db.is_abuse_enabled(chat_id):
            return

        # Admin immune
        if await is_admin(chat_id, user_id):
            return

        # Whitelisted user
        if await db.is_user_whitelisted(chat_id, user_id):
            return

        text = message.text or ""
        detected = False

        # -------- LOCAL WORD CHECK --------
        for word in ABUSIVE_WORDS:
            if re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE):
                detected = True
                break

        # -------- AI TOXICITY CHECK --------
        if not detected and OPENROUTER_API_KEY:
            try:
                detected = await check_toxicity_ai(text)
            except Exception as e:
                print("AI toxicity error:", e)

        if not detected:
            return

        try:
            await message.delete()

            user = message.from_user
            name = "ㅤ" + (user.first_name or "User") + " ㅤ〱"

            reply_text = (
                f"🚫 Hey {name}, your message was removed.\n\n"
                f"🔍 Censored:\n{text.lower()}\n\n"
                f"Please keep the chat respectful."
            )

            sent = await message.reply(reply_text)
            await asyncio.sleep(60)
            await sent.delete()

        except Exception as e:
            print("Abuse watcher error:", e)
