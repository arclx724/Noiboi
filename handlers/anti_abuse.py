import re
import aiohttp
import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import OPENROUTER_API_KEY, BOT_USERNAME
import db

# --- Abusive Words List ---
ABUSIVE_WORDS = [
    "aand", "aad", "asshole", "b.c.", "b.s.d.k", "babbe", "babbey", "bahenchod", 
    "bakchod", "bakchodi", "bakchodd", "bastard", "bc", "behench*d", "behenchod", 
    "bevkuf", "bevakoof", "bevda", "bevdey", "bevkoof", "bewakoof", "bewday", 
    "bewkoof", "bewkuf", "bhadua", "bhaduaa", "bhadva", "bhadvaa", "bhadwa", 
    "bhadwaa", "bhadwe", "bhench0d", "bhenchod", "bhenchodd", "bhosada", "bhosda", 
    "bhosdaa", "bhosadchod", "bhosadchodal", "bhosdike", "bhosdiki", "bhosdiwala", 
    "bhosdiwale", "bhonsdike", "bitch", "bkl", "bsdk", "bube", "bubey", "bur", 
    "burr", "buur", "buurr", "ch*tiya", "charsi", "chhod", "chod", "chodd", 
    "chooche", "choochi", "choot", "chudne", "chudney", "chudwa", "chudwaa", 
    "chudwaane", "chudwane", "chuchi", "chut", "chutad", "chute", "chuteya", 
    "chutia", "chutiya", "chutiyapa", "chutiye", "chuttad", "chutya", "dalaal", 
    "dalal", "dalle", "dalley", "dick", "fattu", "fuck", "g@ndu", "gaand", 
    "gaandfat", "gaandmar", "gaandmara", "gaandmasti", "gadha", "gadhe", 
    "gadhalund", "gand", "gandfat", "gandfut", "gandiya", "gandiye", "gandu", 
    "goo", "gote", "gotey", "gotte", "gu", "hag", "haggu", "hagne", "hagney", 
    "haraami", "haraamjaada", "haraamjaade", "haraamkhor", "haraamzaade", 
    "haraamzyaada", "harami", "haramjada", "haramkhor", "haramzyada", "jhaant", 
    "jhaat", "jhaatu", "jhat", "jhatu", "kamina", "kamine", "kutta", "kutte", 
    "kuttey", "kutti", "kuttia", "kutiya", "kuttiya", "l*da", "l@da", "lauda", 
    "laude", "laudey", "laura", "lavda", "lawda", "ling", "loda", "lode", 
    "lodu", "lora", "launda", "lounde", "loundey", "laundi", "laundiya", 
    "lulli", "lund", "m.c.", "maar", "madarchod", "madarchodd", "madarchood", 
    "madarchoot", "madarchut", "madarxhod", "maderchod", "madherchod", 
    "madherchood", "Madharchod", "Madharchood", "mamme", "mammey", "maro", 
    "marunga", "mc", "mkc", "moot", "mootne", "mooth", "motherfucker", "mut", 
    "mutne", "muth", "nalayak", "nikamma", "nunni", "nunnu", "paaji", "paji", 
    "pesaab", "pesab", "peshaab", "peshab", "pilla", "pillay", "pille", 
    "pilley", "pisaab", "pisab", "pkmkb", "porkistan", "raand", "rand", 
    "randi", "randibaaz", "randy", "ramdi", "saala", "saali", "suar", 
    "tatte", "tatti", "tatty", "tmkc", "ullu"
]

API_URL = "https://openrouter.ai/api/v1/chat/completions"
ABUSE_PATTERN = re.compile(r'\b(' + '|'.join(map(re.escape, ABUSIVE_WORDS)) + r')\b', re.IGNORECASE)

# --- Helpers ---
async def is_admin(chat_id, user_id, app):
    try:
        member = await app.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except:
        return False

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

# ================= WRAPPER FUNCTION (Important) =================

def register_abuse_handlers(app: Client):
    
    @app.on_message(filters.command("abuse") & filters.group)
    async def toggle_abuse(client, message):
        if not await is_admin(message.chat.id, message.from_user.id, app):
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
        if not await is_admin(message.chat.id, message.from_user.id, app):
            return

        target = message.reply_to_message.from_user if message.reply_to_message else None
        if not target:
            return await message.reply_text("⚠️ Reply to a user to auth them.")

        await db.add_whitelist(message.chat.id, target.id)
        await message.reply_text(f"✅ {target.mention} is now whitelisted from abuse filter.")

    @app.on_message(filters.command("unauth") & filters.group)
    async def unauth_user(client, message):
        if not await is_admin(message.chat.id, message.from_user.id, app):
            return

        target = message.reply_to_message.from_user if message.reply_to_message else None
        if not target:
            return await message.reply_text("⚠️ Reply to a user to un-auth them.")

        await db.remove_whitelist(message.chat.id, target.id)
        await message.reply_text(f"🚫 {target.mention} removed from whitelist.")

    @app.on_message(filters.command("authlist") & filters.group)
    async def auth_list(client, message):
        if not await is_admin(message.chat.id, message.from_user.id, app):
            return

        users = await db.get_whitelisted_users(message.chat.id)
        if not users:
            return await message.reply_text("📂 Whitelist is empty.")
        
        text = "📋 **Whitelisted Users:**\n"
        for uid in users:
            try:
                u = await app.get_users(uid)
                text += f"- {u.mention}\n"
            except:
                text += f"- ID: {uid}\n"
        await message.reply_text(text)

    # --- MAIN WATCHER ---
    @app.on_message(filters.group & ~filters.bot, group=10)
    async def abuse_watcher(client, message):
        text = message.text or message.caption
        if not text:
            return

        if not await db.is_abuse_enabled(message.chat.id):
            return

        if await is_admin(message.chat.id, message.from_user.id, app):
            return
        if await db.is_user_whitelisted(message.chat.id, message.from_user.id):
            return

        detected = False
        censored_text = text

        # 1. Local Check
        if ABUSE_PATTERN.search(text):
            detected = True
            censored_text = ABUSE_PATTERN.sub(lambda m: f"||{m.group(0)}||", text)

        # 2. AI Check (Only if not already detected)
        if not detected and OPENROUTER_API_KEY:
            if await check_toxicity_ai(text):
                detected = True
                censored_text = f"||{text}||"

        if detected:
            try:
                await message.delete()
                
                buttons = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("➕ Add Me", url=f"https://t.me/{BOT_USERNAME}?startgroup=true"),
                        InlineKeyboardButton("📢 Updates", url="https://t.me/robokaty")
                    ]
                ])

                clean_name = message.from_user.first_name.replace("[", "").replace("]", "")
                user_link = f"[{clean_name}](tg://user?id={message.from_user.id})"

                warning_text = (
                    f"🚫 Hey {user_link}, your message was removed.\n\n"
                    f"🔍 **Censored:**\n{censored_text}\n\n"
                    f"Please keep the chat respectful."
                )

                sent = await message.reply_text(
                    warning_text,
                    reply_markup=buttons,
                    disable_web_page_preview=True
                )
                await asyncio.sleep(60)
                await sent.delete()
            except Exception as e:
                print(f"Error deleting abuse: {e}")
    
