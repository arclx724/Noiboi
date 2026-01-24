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

    # --- 2. CONFIGURATION COMMANDS ---
    @app.on_message(filters.command(["cleanservice", "keepservice", "nocleanservice"]) & filters.group)
    async def clean_service_config(client, message: Message):
        # Admin Permission Check
        user = await client.get_chat_member(message.chat.id, message.from_user.id)
        if user.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
            return await message.reply_text("❌ Only Admins can change this setting.")

        cmd = message.command[0].lower()
        
        # Usage Check
        if len(message.command) < 2:
            return await message.reply_text("⚠️ **Usage:**\n`/cleanservice <type>` (Delete)\n`/keepservice <type>` (Don't Delete)\n\nExample: `/cleanservice join`")
        
        action_type = message.command[1].lower()
        
        # --- ALIAS LOGIC (on/off/yes/no -> all) ---
        if action_type in ["on", "yes", "enable"]: action_type = "all"
        if action_type in ["off", "no", "disable"]: 
            # "Off" means stop deleting everything
            await db.disable_clean_service(message.chat.id, "all")
            return await message.reply_text("✅ Clean Service **Disabled**. I will keep all service messages.")

        # Validation
        if action_type not in SERVICE_TYPES:
            return await message.reply_text(f"❌ Invalid Type: `{action_type}`.\nTry `/cleanservicetypes` for the list.")

        # --- EXECUTION LOGIC ---
        
        # Case A: /cleanservice (DELETE IT)
        if "clean" in cmd and "no" not in cmd: 
            await db.enable_clean_service(message.chat.id, action_type)
            if action_type == "all":
                await message.reply_text(f"🗑️ **Clean Service:** Deleting **ALL** service messages.")
            else:
                await message.reply_text(f"🗑️ **Clean Service:** Now deleting `{action_type}` messages.")
        
        # Case B: /keepservice or /nocleanservice (KEEP IT)
        else: 
            await db.disable_clean_service(message.chat.id, action_type)
            if action_type == "all":
                await message.reply_text(f"✅ **Keep Service:** Stopped deleting everything.")
            else:
                await message.reply_text(f"✅ **Keep Service:** I will keep `{action_type}` messages.")

    # --- 3. THE DELETER WATCHER ---
    @app.on_message(filters.service, group=1)
    async def service_deleter_watcher(client, message: Message):
        chat_id = message.chat.id
        
        # Database check
        active_types = await db.get_clean_service_types(chat_id)
        if not active_types:
            return

        should_delete = False
        
        # --- CHECK 1: ALL ---
        if "all" in active_types:
            should_delete = True
        
        # --- CHECK 2: SPECIFIC TYPES ---
        else:
            # 1. JOIN (New Members)
            if message.new_chat_members:
                if "join" in active_types: should_delete = True
            
            # 2. LEAVE (Left/Removed)
            elif message.left_chat_member:
                if "leave" in active_types: should_delete = True
            
            # 3. PHOTO (Chat Photo Changed/Deleted)
            elif message.new_chat_photo or message.delete_chat_photo:
                if "photo" in active_types: should_delete = True
            
            # 4. PIN (Pinned Message)
            elif message.pinned_message:
                if "pin" in active_types: should_delete = True
            
            # 5. TITLE (Chat Title Changed)
            elif message.new_chat_title:
                if "title" in active_types: should_delete = True
            
            # 6. VIDEOCHAT (Voice Chat Actions)
            elif (message.video_chat_started or 
                  message.video_chat_ended or 
                  message.video_chat_members_invited or 
                  message.video_chat_scheduled):
                if "videochat" in active_types: should_delete = True
            
            # 7. OTHER (Misc Items)
            elif "other" in active_types:
                # Covering: Boosts, Payments, Proximity, Auto-Delete, WebApp, Topics
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
                    # Note: 'chat_boost_added' works in newer Pyrogram versions
                    getattr(message, "chat_boost_added", False)):
                    should_delete = True

        # Final Execution
        if should_delete:
            try:
                await message.delete()
            except:
                pass 
