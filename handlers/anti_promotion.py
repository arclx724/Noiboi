import requests
import re
import unicodedata
from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus, MessageEntityType
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import OPENROUTER_API_KEY, BOT_USERNAME, SUPPORT_GROUP
import db

# --- CONFIGURATION ---
# Catch t.me, telegram.me, and standard http links
LINK_REGEX = r"(https?://|www\.|t\.me|telegram\.me|tg://)"
MENTION_REGEX = r"@"

def normalize_text(text):
    """
    Aggressive cleaning of fancy fonts to standard English.
    """
    if not text: return ""
    
    # 1. Standard Unicode Normalization
    normalized = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    
    # 2. Fallback: Agar upar wala fail ho jaye, toh manually check karo
    # (Example: Spammers use specific ranges for bold/italic)
    return normalized.lower()

def check_promo_with_ai(text):
    """
    OpenRouter AI check.
    """
    try:
        clean_text = normalize_text(text)
        print(f"DEBUG: AI Checking text: {clean_text[:50]}...") # Log 1
        
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
            result = response.json()['choices'][0]['message']['content'].strip().upper()
            print(f"DEBUG: AI Result: {result}") # Log 2
            return "YES" in result
        return False
    except Exception as e:
        print(f"DEBUG: AI Error: {e}")
        return False

def register_antipromo_handlers(app: Client):

    @app.on_message(filters.command("nopromo") & filters.group)
    async def nopromo_switch(client, message):
        user = await client.get_chat_member(message.chat.id, message.from_user.id)
        if user.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            await message.reply_text("You need to be an admin to do this.")
            return

        if len(message.command) > 1:
            arg = message.command[1].lower()
            if arg == "on":
                await db.set_antipromo_status(message.chat.id, True)
                await message.reply_text("⛔ **No-Promo System Enabled!**\nScanning for bots and ads...")
            elif arg == "off":
                await db.set_antipromo_status(message.chat.id, False)
                await message.reply_text("✅ **No-Promo System Disabled!**")
        else:
            await message.reply_text("Usage: `/nopromo on` or `/nopromo off`")

    # ======================================================
    # MAIN WATCHER
    # ======================================================
    
    @app.on_message(filters.group, group=40)
    async def promo_detector(client, message):
        chat_id = message.chat.id
        
        if not await db.is_antipromo_enabled(chat_id):
            return

        # --- DEBUGGING PRINTS (Check your terminal when spam comes) ---
        # Yeh batayega ki bot message dekh raha hai ya nahi
        
        # 1. Skip if message is empty
        raw_text = message.text or message.caption or ""
        if not raw_text: return

        # 2. Check Permissions
        try:
            me = await client.get_chat_member(chat_id, "me")
            if not me.privileges.can_delete_messages:
                # print("DEBUG: I don't have delete permission!")
                return
        except:
            return

        clean_text = normalize_text(raw_text)
        is_guilty = False
        reason = ""

        # --- CHECK 1: BOT DETECTION ---
        if message.from_user and message.from_user.is_bot:
            print(f"DEBUG: Bot Message Detected from {message.from_user.first_name}")
            
            # Rule 1: Link Check
            if re.search(LINK_REGEX, raw_text):
                is_guilty = True
                reason = "Bot sent a Link"
            
            # Rule 2: Keywords (Join, DM, etc.)
            elif "join" in clean_text or "dm me" in clean_text or "click here" in clean_text:
                is_guilty = True
                reason = "Bot sent Ad keywords"
            
            # Rule 3: Forwarding
            elif message.forward_date or message.forward_from:
                is_guilty = True
                reason = "Bot Forwarding"

        # --- CHECK 2: HUMAN DETECTION ---
        elif message.from_user and not message.from_user.is_bot:
            # Skip Admins
            try:
                user = await client.get_chat_member(chat_id, message.from_user.id)
                if user.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                    return
            except:
                pass

            # Check if text contains Link or Mention
            has_link = re.search(LINK_REGEX, raw_text)
            has_mention = re.search(MENTION_REGEX, raw_text)
            
            # Also check text entities (Hyperlinks hidden in text)
            if message.entities:
                for ent in message.entities:
                    if ent.type in [MessageEntityType.URL, MessageEntityType.TEXT_LINK, MessageEntityType.MENTION]:
                        has_link = True
            
            if has_link or has_mention:
                print(f"DEBUG: Checking potential human spam from {message.from_user.first_name}")
                if check_promo_with_ai(raw_text):
                    is_guilty = True
                    reason = "AI detected Promotion"

        # --- ACTION: DELETE ---
        if is_guilty:
            print(f"DEBUG: DELETING Message! Reason: {reason}")
            try:
                await message.delete()
                
                if not message.from_user.is_bot:
                    warn_text = f"⛔ **No Promotions!**\nAction: **Deleted** 🗑️"
                    await message.reply_text(warn_text)
                    
            except Exception as e:
                print(f"DEBUG: DELETE FAILED: {e}")
                # AGAR YE ERROR AATA HAI: "MESSAGE_DELETE_FORBIDDEN" 
                # TOH ISKA MATLAB WO SPAMMER BOT 'ADMIN' HAI.
                
