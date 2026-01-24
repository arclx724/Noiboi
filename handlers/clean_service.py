from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus
import db

# ================= CATEGORIES =================
SERVICE_TYPES = {
    "join": "New members joining",
    "leave": "Members leaving",
    "pin": "Pinned messages",
    "photo": "Chat photo/background updates",
    "title": "Chat title updates",
    "videochat": "Video chat actions",
    "other": "Misc (Payment, Boosts, Prox. Alert)",
    "all": "All service messages"
}

def register_clean_service_handlers(app: Client):

    # --- 1. LIST TYPES COMMAND ---
    @app.on_message(filters.command("cleanservicetypes") & filters.group)
    async def list_types(client, message):
        text = "🧹 **Available Service Types:**\n\n"
        for k, v in SERVICE_TYPES.items():
            text += f"• `{k}`: {v}\n"
        text += "\n**Usage:** `/cleanservice <type>` to delete, `/keepservice <type>` to stop deleting."
        await message.reply_text(text)

    # --- 2. CONFIGURATION COMMANDS ---
    @app.on_message(filters.command(["cleanservice", "keepservice", "nocleanservice"]) & filters.group)
    async def clean_service_config(client, message: Message):
        # Admin Permission Check
        user = await client.get_chat_member(message.chat.id, message.from_user.id)
        if user.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
            return await message.reply_text("❌ Only Admins can change this setting.")

        cmd = message.command[0].lower()
        if len(message.command) < 2:
            return await message.reply_text("⚠️ **Usage:** `/cleanservice <type>` or `/keepservice <type>`\nSee `/cleanservicetypes` for list.")
        
        action_type = message.command[1].lower()
        
        # --- 🛠️ CHANGE HERE: ON Logic ---
        if action_type in ["on", "enable"]:
            # Sirf message bhejenge, kuch set nahi karenge (Standby Mode)
            return await message.reply_text(
                "✅ **Clean Service is ON (Standby).**\n\n"
                "Abhi maine kuch delete karna shuru nahi kiya hai.\n"
                "Delete shuru karne ke liye type batayein:\n"
                "👉 `/cleanservice join` (Sirf joins ke liye)\n"
                "👉 `/cleanservice all` (Sab kuch udane ke liye)"
            )

        # OFF Logic
        if action_type in ["off", "no", "disable"]: 
            await db.disable_clean_service(message.chat.id, "all")
            return await message.reply_text("✅ Clean Service **Disabled**. Service messages will stay.")

        # Type Validation
        if action_type not in SERVICE_TYPES:
            return await message.reply_text(f"❌ Invalid Type: `{action_type}`. Check `/cleanservicetypes`.")

        # Logic
        if "clean" in cmd and "no" not in cmd: # /cleanservice
            await db.enable_clean_service(message.chat.id, action_type)
            await message.reply_text(f"✅ **Enabled:** Now deleting `{action_type}` messages.")
        else: # /keepservice or /nocleanservice
            await db.disable_clean_service(message.chat.id, action_type)
            await message.reply_text(f"✅ **Disabled:** Stopped deleting `{action_type}` messages.")

    # --- 3. THE DELETER WATCHER ---
    @app.on_message(filters.service, group=1)
    async def service_deleter_watcher(client, message: Message):
        chat_id = message.chat.id
        
        # Database se pucho kya delete karna hai
        active_types = await db.get_clean_service_types(chat_id)
        
        if not active_types:
            return

        should_delete = False
        
        # A. Check "ALL"
        if "all" in active_types:
            should_delete = True
        else:
            # B. Check Specific Types
            if message.new_chat_members and "join" in active_types: should_delete = True
            elif message.left_chat_member and "leave" in active_types: should_delete = True
            elif message.pinned_message and "pin" in active_types: should_delete = True
            elif (message.new_chat_photo or message.delete_chat_photo) and "photo" in active_types: should_delete = True
            elif message.new_chat_title and "title" in active_types: should_delete = True
            elif (message.video_chat_started or message.video_chat_ended or message.video_chat_members_invited or message.video_chat_scheduled) and "videochat" in active_types: should_delete = True
            elif "other" in active_types:
                if (message.successful_payment or message.proximity_alert_triggered or message.message_auto_delete_timer_changed or message.web_app_data or message.general_topic_hidden or message.general_topic_unhidden or message.forum_topic_created or message.forum_topic_edited or message.forum_topic_closed or message.forum_topic_reopened):
                    should_delete = True

        if should_delete:
            try: await message.delete()
            except: pass
                
