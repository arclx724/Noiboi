import re
import asyncio
from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import Message

from config import OPENROUTER_API_KEY
import db


# ---------------- ABUSIVE WORDS ----------------
ABUSIVE_WORDS = [
    "madarchod", "behenchod", "mc", "bc", "bsdk",
    "bhosdike", "chutiya", "gandu", "lodu", "lauda",
    "lund", "jhant", "chut", "tatte", "gaand",
    "kamina", "harami", "saala", "kutte",
    "randi", "bkl", "fuck", "bitch", "asshole",
    "motherfucker", "dick", "tmkc", "mkc"
]


# ---------------- ADMIN CHECK ----------------
async def is_admin(app, chat_id: int, user_id: int) -> bool:
    try:
        member = await app.get_chat_member(chat_id, user_id)
        return member.status in (
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        )
    except Exception:
        return False


# ---------------- ABUSE HANDLER ----------------
def register_abuse_handlers(app):

    @app.on_message(filters.text & filters.group & ~filters.bot, group=10)
    async def abuse_watcher(_, message: Message):

        if not message.from_user:
            return

        chat_id = message.chat.id
        user_id = message.from_user.id
        text = message.text or ""

        # Feature enabled?
        if not await db.is_abuse_enabled(chat_id):
            return

        # Admin immune
        if await is_admin(app, chat_id, user_id):
            return

        # Whitelisted
        if await db.is_user_whitelisted(chat_id, user_id):
            return

        detected = False

        # -------- LOCAL WORD CHECK --------
        for word in ABUSIVE_WORDS:
            if re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE):
                detected = True
                break

        # -------- AI CHECK (OPTIONAL) --------
        if not detected and OPENROUTER_API_KEY:
            try:
                from ai.toxicity import check_toxicity_ai
                detected = await check_toxicity_ai(text)
            except Exception as e:
                print("AI check failed:", e)

        if not detected:
            return

        try:
            await message.delete()

            name = "ㅤ" + (message.from_user.first_name or "User") + " ㅤ〱"

            reply_text = (
                f"🚫 Hey {name}, your message was removed.\n\n"
                f"🔍 Censored:\n{text.lower()}\n\n"
                f"Please keep the chat respectful."
            )

            sent = await message.reply(reply_text)
            await asyncio.sleep(60)
            await sent.delete()

        except Exception as e:
            print("Abuse handler error:", e)
