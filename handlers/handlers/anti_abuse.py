import re
import aiohttp
import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus, ParseMode
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import OPENROUTER_API_KEY, BOT_USERNAME
import db

# Print message to confirm NEW code is loaded
print("✅ NEW ANTI_ABUSE MODULE LOADED")

# Abusive Words List
ABUSIVE_WORDS = [
    "madarchod", "Madharchod", "Madharchood", "behenchod", "madherchood", "madherchod", "bhenchod", "maderchod", "mc", "bc", "bsdk", 
    "bhosdike", "bhosdiwala", "chutiya", "chutiyapa", "gandu", "gand", 
    "lodu", "lode", "lauda", "lund", "lawda", "lavda", "aand", "jhant", 
    "jhaant", "chut", "chuchi", "tatte", "tatti", "gaand", "gaandmar", 
    "gaandmasti", "gaandfat", "gaandmara", "kamina", "kamine", "harami", 
    "haraami", "nalayak", "nikamma", "kutte", "kutta", "kutti", "saala", 
    "saali", "bhadwa", "bhadwe", "randi", "randibaaz", "bkl", "l*da", 
    "l@da", "ch*tiya", "g@ndu", "behench*d", "bhench0d", "madarxhod", 
    "chutya", "chuteya", "rand", "ramdi", "choot", "bhosda", "fuck", 
    "bitch", "bastard", "asshole", "motherfucker", "dick", "tmkc", "mkc"
]

API_URL = "https://openrouter.ai/api/v1/chat/completions"

def register_abuse_handlers(app: Client):

    # --- Helper: Check Admin ---
    async def is_admin(chat_id, user_id):
        try:
            member = await app.get_chat_member(chat_id, user_id)
            return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
        except:
            return False

    # --- AI Helper Function ---
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
                    "content": "You are a content filter. Reply ONLY with 'YES' if the message contains hate speech, severe abuse, or extreme profanity. Reply 'NO' if safe."
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
                        answer = data['choices'][0]['message']['content'].strip().upper()
                        return "YES" in answer
        except Exception:
            return False
        return False

    # ================= COMMANDS =================

    @app.on_message(filters.command("abuse") & filters.group)
    async def toggle_abuse(client, message):
        if not await is_admin(message.chat.id, message.from_user.id):
            return await message.reply_text("❌ Only admins can use this.")

        if len(message.command) > 1:
            arg = message.command[1].lower()
            new_status = arg in ["on", "enable", "yes"]
        else:
            current = await db.is_abuse_enabled(message.chat.id)
            new_status = not current
        
        await db.set_abuse_status(message.chat.id, new_status)
        state = "Enabled ✅" if new_status else "Disabled ❌"
        await message.reply_text(f"🛡 Abuse protection is now {state}")

    @app.on_message(filters.command(["auth", "promote"]) & filters.group)
    async def auth_user(client, message):
        if not await is_admin(message.chat.id, message.from_user.id):
            return

        target = message.reply_to_message.from_user if message.reply_to_message else None
        if not target:
            return await message.reply_text("⚠️ Reply to a user to auth them.")

        await db.add_whitelist(message.chat.id, target.id)
        await message.reply_text(f"✅ {target.mention} is now whitelisted from abuse filter.")

    @app.on_message(filters.command("unauth") & filters.group)
    async def unauth_user(client, message):
        if not await is_admin(message.chat.id, message.from_user.id):
            return

        target = message.reply_to_message.from_user if message.reply_to_message else None
        if not target:
            return await message.reply_text("⚠️ Reply to a user to un-auth them.")

        await db.remove_whitelist(message.chat.id, target.id)
        await message.reply_text(f"🚫 {target.mention} removed from whitelist.")

    @app.on_message(filters.command("authlist") & filters.group)
    async def auth_list(client, message):
        if not await is_admin(message.chat.id, message.from_user.id):
            return

        users = await db.get_whitelisted_users(message.chat.id)
        if not users:
            return await message.reply_text("📂 Whitelist is empty.")
        
        text = "📋 **Whitelisted Users:**\n"
        for uid in users:
            try:
                u = await client.get_users(uid)
                text += f"- {u.mention}\n"
            except:
                text += f"- ID: {uid}\n"
        await message.reply_text(text)

    # ================= WATCHER (Group=10) =================
    
    @app.on_message(filters.text & filters.group & ~filters.bot, group=10)
    async def abuse_watcher(client, message):
        if not await db.is_abuse_enabled(message.chat.id):
            return

        if await is_admin(message.chat.id, message.from_user.id):
            return
        if await db.is_user_whitelisted(message.chat.id, message.from_user.id):
            return

        text = message.text
        censored_text = text
        detected = False

        # 1. Local Check
        for word in ABUSIVE_WORDS:
            pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
            if pattern.search(censored_text):
                detected = True
                censored_text = pattern.sub(lambda match: f"||{match.group(0)}||", censored_text)

        # 2. AI Check (Fallback)
        if not detected and OPENROUTER_API_KEY:
            if await check_toxicity_ai(text):
                detected = True
                censored_text = f"||{text}||"

        # 3. Action
        if detected:
            try:
                await message.delete()
                
                # BUTTONS (Exact Match Security Bot)
                buttons = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("➕ Add Me", url=f"https://t.me/{BOT_USERNAME}?startgroup=true"),
                        InlineKeyboardButton("📢 Updates", url="https://t.me/world_bfc_zonee")
                    ]
                ])

                # MENTION (Exact Match Security Bot - Blue Link)
                # Hum brackets hata rahe hain taaki format na toote
                clean_name = message.from_user.first_name.replace("[", "").replace("]", "")
                user_link = f"[{clean_name}](tg://user?id={message.from_user.id})"

                # WARNING TEXT (Exact Match)
                warning_text = (
                    f"🚫 Hey {user_link}, your message was removed.\n\n"
                    f"🔍 **Censored:**\n{censored_text}\n\n"
                    f"Please keep the chat respectful."
                )

                user_name = message.from_user.first_name or "User"
user_id = message.from_user.id

mention_html = f'<a href="tg://user?id={user_id}">{user_name}</a>'

warning_text = (
    f"🚫 Hey {mention_html}, your message was removed.\n\n"
    f"🔍 <b>Censored:</b>\n"
    f"<spoiler>{text}</spoiler>\n\n"
    f"⚠️ Please be respectful."
)

sent = await message.reply_text(
    warning_text,
    reply_markup=buttons,
    parse_mode=ParseMode.HTML,
    disable_web_page_preview=True
)
                await asyncio.sleep(60)
                await sent.delete()
            except Exception as e:
                print(f"Error deleting abuse: {e}")
                
