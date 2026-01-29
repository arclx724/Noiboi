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
    "aand", "aandu", "aad", "ass", "asshole", "b.c", "b.c.", "b.k.l", "b.s.d.k", 
    "babbe", "babbey", "bahenchod", "bahenchodd", "bakchod", "bakchodi", "bakchodd", 
    "bastard", "bc", "behench*d", "behenchod", "behenchodd", "behenka", "betichod", 
    "bevakoof", "bevda", "bevdey", "bevkoof", "bewakoof", "bewday", "bewkoof", "bewkuf", 
    "bhadua", "bhaduaa", "bhadva", "bhadvaa", "bhadwa", "bhadwaa", "bhadwe", "bhadwes", 
    "bhench0d", "bhenchod", "bhenchodd", "bhosada", "bhosda", "bhosdaa", "bhosadchod", 
    "bhosadchodal", "bhosdike", "bhosdiki", "bhosdiwala", "bhosdiwale", "bhonsdike", 
    "bitch", "bkl", "blowjob", "boobs", "boor", "bsdk", "bube", "bubey", "bullshit", 
    "bur", "burchodi", "burr", "buur", "buurr", "ch*tiya", "charsi", "chhakka", 
    "chhenal", "chhi", "chhin", "chhod", "chinaal", "chinal", "chipkali", "chod", 
    "chodd", "chodai", "chodna", "chodne", "choodai", "chooche", "choochi", "choot", 
    "chootia", "chudai", "chudakkad", "chudne", "chudney", "chudwa", "chudwaa", 
    "chudwaane", "chudwane", "chuchi", "chut", "chutad", "chute", "chuteya", "chutia", 
    "chutiya", "chutiyapa", "chutiye", "chuttad", "chutya", "cock", "cunt", "dalaal", 
    "dalal", "dalle", "dalley", "dalli", "dick", "dickhead", "doggy", "fattu", 
    "fuck", "fucker", "fucking", "g@ndu", "gaand", "gaandfat", "gaandmasti", 
    "gaandmar", "gaandmara", "gaandu", "gadha", "gadhe", "gadhalund", "gand", 
    "gandfat", "gandfut", "gandi", "gandiya", "gandiye", "gandu", "gandve", "gay", 
    "goo", "gote", "gotey", "gotte", "gu", "hag", "haggu", "hagne", "hagney", 
    "haraami", "haraamjaada", "haraamjaade", "haraamkhor", "haraamzaade", 
    "haraamzyaada", "harami", "haramjada", "haramkhor", "haramzyada", "hijra", 
    "jhaant", "jhaat", "jhaatu", "jhat", "jhatu", "kamin", "kamina", "kamine", 
    "kaminey", "kanjar", "kanjari", "kutta", "kutte", "kuttey", "kutti", "kuttia", 
    "kutiya", "kuttiya", "l*da", "l@da", "lauda", "laude", "laudey", "laura", 
    "lavda", "lavde", "lawda", "lesbian", "ling", "loda", "lode", "lodu", "lora", 
    "loru", "launda", "lounde", "loundey", "laundi", "laundiya", "lulli", "lund", 
    "lundchus", "m.c", "m.c.", "maar", "madarchod", "madarchodd", "madarchood", 
    "madarchoot", "madarchut", "madarxhod", "maderchod", "madherchod", "madherchood", 
    "Madharchod", "Madharchood", "mamme", "mammey", "maro", "marunga", "mc", "mf", 
    "mkc", "moot", "mootne", "mooth", "motherfucker", "mut", "mutne", "muth", 
    "mutthal", "nude", "nudes", "nalayak", "nikamma", "nipple", "nunni", "nunnu", 
    "paaji", "paji", "penis", "pesaab", "pesab", "peshaab", "peshab", "pilla", 
    "pillay", "pille", "pilley", "pisaab", "pisab", "pkmkb", "porn", "porno", 
    "pornography", "porns", "porkistan", "pussy", "raand", "rand", "randi", 
    "randibaaz", "randwa", "randy", "ramdi", "rape", "rapist", "saala", "saale", 
    "saali", "sex", "sexting", "sexy", "shit", "slut", "suar", "suwar", "tatte", 
    "tatti", "tatty", "terimaaki", "terimaki", "tmkb", "tmkc", "tits", "ullu", 
    "vagina", "whore", "xxx", "zandu"
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

        # Yahan se maine "is_admin" wala check hata diya hai.
        # Ab ye sabke messages check karega, chahe wo admin ho ya owner.

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
                # Agar bot admin nahi hai ya uske paas admin ko delete karne ki power nahi hai,
                # to yahan error aayega (jo print ho jayega).
                print(f"Error deleting abuse: {e}")
