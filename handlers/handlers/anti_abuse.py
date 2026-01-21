import re
import aiohttp
import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus, ParseMode
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from config import OPENROUTER_API_KEY, BOT_USERNAME
import db

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
                        print(f"🤖 AI Response: {answer}")  # DEBUG PRINT
                        return "YES" in answer
        except Exception as e:
            print(f"❌ AI Check Error: {e}")
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

    # ================= WATCHER (Group=10) =================
    
    @app.on_message(filters.text & filters.group & ~filters.bot, group=10)
    async def abuse_watcher(client, message):
        
        # 1. Check if Enabled
        if not await db.is_abuse_enabled(message.chat.id):
            # print("Skipping: Abuse filter is OFF in this chat.") 
            return

        # 2. Check if Admin (Admins are immune!)
        # Agar aap Owner/Admin ho toh yahan se return ho jayega.
        # Test karne ke liye kisi normal member id se check karo.
        if await is_admin(message.chat.id, message.from_user.id):
            print(f"Skipping: User {message.from_user.first_name} is Admin.")
            return

        # 3. Check Whitelist
        if await db.is_user_whitelisted(message.chat.id, message.from_user.id):
            print(f"Skipping: User {message.from_user.first_name} is Whitelisted.")
            return

        text = message.text
        censored_text = text
        detected = False

        # 4. Local Word Check
        for word in ABUSIVE_WORDS:
            pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
            if pattern.search(censored_text):
                detected = True
                print(f"🤬 Abuse Detected (Local): {word}") # DEBUG PRINT
                censored_text = pattern.sub(lambda match: f"||{match.group(0)}||", censored_text)

        # 5. AI Check (Fallback)
        if not detected and OPENROUTER_API_KEY:
            # print("Checking with AI...")
            if await check_toxicity_ai(text):
                detected = True
                print("🤖 Abuse Detected (AI)") # DEBUG PRINT
                censored_text = f"||{text}||"

        # 6. Action: DELETE
        if detected:
            try:
                await message.delete()
                print("🗑 Message Deleted Successfully") # DEBUG PRINT
                
                buttons = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📢 Updates", url=f"https://t.me/{BOT_USERNAME}")]
                ])

                warning_text = (
                    f"🚫 Hey {message.from_user.mention}, message removed!\n\n"
                    f"🔍 **Censored:**\n{censored_text}\n\n"
                    f"⚠️ Please be respectful."
                )

                sent = await message.reply_text(
                    warning_text,
                    reply_markup=buttons,
                    parse_mode=ParseMode.MARKDOWN
                )
                await asyncio.sleep(60)
                await sent.delete()
            except Exception as e:
                print(f"❌ Error deleting abuse: {e}")
                
