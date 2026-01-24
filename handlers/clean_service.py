import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus
import db

# ================= 📚 CATEGORIES DEFINITION =================
SERVICE_TYPES = {
    "all": "All service messages.",
    "join": "When a new user joins, or is added.",
    "leave": "When a user leaves, or is removed.",
    "photo": "When chat photos or chat backgrounds are changed.",
    "pin": "When a new message is pinned.",
    "title": "When chat or topic titles are changed.",
    "videochat": "Video chat actions (start, end, schedule, invite).",
    "other": "Misc (Boosts, Payments, Auto-Delete, Topics, etc)."
}

def register_clean_service_handlers(app: Client):

    # --- 1. LIST COMMAND (/cleanservicetypes) ---
    @app.on_message(filters.command("cleanservicetypes") & filters.group)
    async def list_types(client, message):
        text = "🧹 **Available Service Types:**\n\n"
        for k, v in SERVICE_TYPES.items():
            if k == "all": continue
            text += f"• `{k}`: {v}\n"
        
        text += f"\n• `all`: {SERVICE_TYPES['all']}\n"
        text += "\n**Commands:**\n"
        text += "• `/cleanservice <type>`: Start deleting messages.\n"
        text += "• `/keepservice <type>`: Stop deleting messages.\n"
        text += "• `/cleanservice all`: Stop ALL service messages."
        
        await message.reply_text(text)

    # --- 2. CONFIGURATION COMMANDS (SILENT MODE) ---
    @app.on_message(filters.command(["cleanservice", "keepservice", "nocleanservice"]) & filters.group)
    async def clean_service_config(client, message: Message):
        # Admin Permission Check
        user = await client.get_chat_member(message.chat.id, message.from_user.id)
        if user.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
            msg = await message.reply_text("❌ Only Admins.")
            await asyncio.sleep(3)
            await msg.delete()
            return

        # Alias / Usage Logic
        if len(message.command) < 2:
            msg = await message.reply_text("⚠️ Usage: `/cleanservice <type>`")
            await asyncio.sleep(3)
            await msg.delete()
            return
        
        cmd = message.command[0].lower()
        action_type = message.command[1].lower()
        
        if action_type in ["on", "yes", "enable"]: action_type = "all"
        if action_type in ["off", "no", "disable"]: 
            await db.disable_clean_service(message.chat.id, "all")
            msg = await message.reply_text("✅ Disabled.")
            await asyncio.sleep(3)
            await msg.delete()
            return

        if action_type not in SERVICE_TYPES:
            msg = await message.reply_text(f"❌ Invalid Type: `{action_type}`")
            await asyncio.sleep(3)
            await msg.delete()
            return

        # --- EXECUTION (SILENT) ---
        
        # 1. Database Update
        if "clean" in cmd and "no" not in cmd: 
            await db.enable_clean_service(message.chat.id, action_type)
            status_emoji = "🗑️" # Deleting
        else: 
            await db.disable_clean_service(message.chat.id, action_type)
            status_emoji = "✅" # Keeping

        # 2. Cleanup User Command (Taaki chat saaf rahe)
        try:
            await message.delete()
        except:
            pass

        # 3. Temp Confirmation (3 Sec baad gayab)
        # Bada message hata diya, ab sirf emoji aayega jo gayab ho jayega
        confirm_msg = await message.reply_text(f"{status_emoji} Updated: `{action_type}`")
        await asyncio.sleep(3)
        try:
            await confirm_msg.delete()
        except:
            pass

    # --- 3. THE DELETER WATCHER ---
    @app.on_message(filters.service, group=1)
    async def service_deleter_watcher(client, message: Message):
        chat_id = message.chat.id
        
        active_types = await db.get_clean_service_types(chat_id)
        if not active_types:
            return

        should_delete = False
        
        if "all" in active_types:
            should_delete = True
        else:
            if message.new_chat_members and "join" in active_types: should_delete = True
            elif message.left_chat_member and "leave" in active_types: should_delete = True
            elif (message.new_chat_photo or message.delete_chat_photo) and "photo" in active_types: should_delete = True
            elif message.pinned_message and "pin" in active_types: should_delete = True
            elif message.new_chat_title and "title" in active_types: should_delete = True
            elif (message.video_chat_started or message.video_chat_ended or message.video_chat_members_invited or message.video_chat_scheduled) and "videochat" in active_types: should_delete = True
            elif "other" in active_types:
                if (message.successful_payment or 
                    message.proximity_alert_triggered or 
                    message.message_auto_delete_timer_changed or 
                    message.web_app_data or
                    message.general_topic_hidden or 
                    message.general_topic_unhidden or 
                    message.forum_topic_created or 
                    message.forum_topic_edited or 
                    message.forum_topic_closed or 
                    message.forum_topic_reopened or
                    getattr(message, "chat_boost_added", False)):
                    should_delete = True

        if should_delete:
            try:
                await message.delete()
            except:
                pass 
