import requests
import re
import unicodedata
from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import OPENROUTER_API_KEY, BOT_USERNAME, SUPPORT_GROUP
import db

# --- CONFIGURATION ---
# Regex to find links (t.me, telegram.me, http://, etc.)
LINK_REGEX = r"(https?://|www\.|t\.me/|telegram\.me/|tg://openmessage)"
MENTION_REGEX = r"@"

def normalize_text(text):
    """
    Fancy fonts (𝐇𝐞𝐥𝐥𝐨) ko normal text (Hello) mein convert karta hai.
    """
    if not text: return ""
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')

def check_promo_with_ai(text):
    """
    OpenRouter AI se check karega ki message Promotion hai ya nahi.
    """
    try:
        # Send normalized text to AI for better understanding
        clean_text = normalize_text(text)
        
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "google/gemini-2.0-flash-001",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a strict Telegram Group Moderator. Analyze the message. "
                            "If it is PROMOTING another Group, Channel, Bot, Event, or asking to Join/DM, "
                            "reply 'YES'. Otherwise reply 'NO'. Ignore fancy fonts."
                        )
                    },
                    {"role": "user", "content": f"Message: {clean_text}"}
                ]
            },
            timeout=5
        )
        
        if response.status_code == 200:
            return "YES" in response.json()['choices'][0]['message']['content'].strip().upper()
        return False
    except:
        return False

def register_antipromo_handlers(app: Client):

    # ======================================================
    # 1. ENABLE / DISABLE COMMAND (/nopromo)
    # ======================================================
    
    @app.on_message(filters.command("nopromo") & filters.group)
    async def nopromo_switch(client, message):
        # Admin Check
        user = await client.get_chat_member(message.chat.id, message.from_user.id)
        if user.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            await message.reply_text("You need to be an admin to do this.")
            return

        if len(message.command) > 1:
            arg = message.command[1].lower()
            if arg == "on":
                await db.set_antipromo_status(message.chat.id, True)
                await message.reply_text("⛔ **No-Promo System Enabled!**\n- Bots forwarding messages will be deleted.\n- Ad messages will be auto-deleted.")
            elif arg == "off":
                await db.set_antipromo_status(message.chat.id, False)
                await message.reply_text("✅ **No-Promo System Disabled!**")
        else:
            await message.reply_text("Usage: `/nopromo on` or `/nopromo off`")

    # ======================================================
    # 2. PROMOTION & BOT WATCHER
    # ======================================================
    
    @app.on_message(filters.group, group=40)
    async def promo_detector(client, message):
        chat_id = message.chat.id
        
        # 1. Check if Enabled
        if not await db.is_antipromo_enabled(chat_id):
            return

        # 2. Check Bot Permissions (Pre-check)
        try:
            me = await client.get_chat_member(chat_id, "me")
            if me.status != ChatMemberStatus.ADMINISTRATOR or not me.privileges.can_delete_messages:
                return # Power nahi hai toh kuch nahi kar sakte
        except:
            return

        is_guilty = False
        reason = ""

        # Normalize Text (Fancy Font Fix)
        raw_text = message.text or message.caption or ""
        clean_text = normalize_text(raw_text).lower()

        # --- CASE A: SENDER IS A BOT ---
        if message.from_user and message.from_user.is_bot:
            # Rule: Agar Bot ne koi bhi message FORWARD kiya -> DELETE
            if message.forward_date or message.forward_from or message.forward_from_chat:
                is_guilty = True
                reason = "Bot Forwarding"
            
            # Rule: Agar Bot ne Link/Promotion bheja -> DELETE
            # (Check normalized text for 'join', 'dm', etc.)
            elif raw_text:
                if re.search(LINK_REGEX, raw_text) or "join" in clean_text or "dm me" in clean_text:
                    is_guilty = True
                    reason = "Bot Promotion"

        # --- CASE B: SENDER IS A HUMAN ---
        elif message.from_user and not message.from_user.is_bot:
            # Admins ko skip karo
            try:
                user = await client.get_chat_member(chat_id, message.from_user.id)
                if user.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                    return
            except:
                pass

            if not raw_text: return

            # AI Check sirf tab kare jab Link ya @ Mention ho
            if re.search(LINK_REGEX, raw_text) or re.search(MENTION_REGEX, raw_text):
                if check_promo_with_ai(raw_text):
                    is_guilty = True
                    reason = "User Promotion"

        # --- ACTION: DELETE ---
        if is_guilty:
            try:
                await message.delete()
                
                # Sirf Humans ke liye Warning bhejo
                if not message.from_user.is_bot:
                    warn_text = (
                        f"⛔ **No Promotions!**\n"
                        f"Hey {message.from_user.mention}, ads allowed nahi hain!\n"
                        f"Action: **Deleted** 🗑️"
                    )
                    await message.reply_text(warn_text)
                    
            except Exception as e:
                # Agar Bot Admin hai aur delete nahi ho raha
                print(f"DEBUG: Delete Failed (Shayad Admin Bot hai): {e}")
                # Optional: Agar Bot message delete nahi kar paya toh report kare
                # await message.reply_text("⚠️ I detected a spam bot but I can't delete its message! It might be an Admin.")
                
