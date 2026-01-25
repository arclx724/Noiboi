import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus
import db

def register_media_delete_handlers(app: Client):

    # --- 1. CONFIGURATION COMMAND (/setdelay) ---
    @app.on_message(filters.command("setdelay") & filters.group)
    async def set_delay_handler(client, message: Message):
        chat_id = message.chat.id
        user_id = message.from_user.id

        # --- PERMISSION CHECK ---
        # Owner check
        member = await client.get_chat_member(chat_id, user_id)
        if member.status != ChatMemberStatus.OWNER:
            # Admin check with specific permissions
            if member.status == ChatMemberStatus.ADMINISTRATOR:
                privileges = member.privileges
                if not (privileges.can_change_info and privileges.can_delete_messages):
                    return await message.reply_text("❌ You need **Change Info** & **Delete Messages** rights.")
            else:
                return await message.reply_text("❌ Only Admins can use this.")

        # --- ARGUMENT PARSING ---
        if len(message.command) < 2:
            return await message.reply_text(
                "⚠️ **Usage:**\n"
                "• `/setdelay on` or `/setdelay off`\n"
                "• `/setdelay 10 s` (Seconds)\n"
                "• `/setdelay 5 m` (Minutes)\n"
                "• `/setdelay 1 h` (Hours)"
            )

        arg1 = message.command[1].lower()

        # A. HANDLE ON/OFF
        if arg1 == "off":
            await db.set_media_delete_status(chat_id, False)
            return await message.reply_text("📴 **Media Auto-Delete is OFF.**")
        
        if arg1 == "on":
            await db.set_media_delete_status(chat_id, True)
            # Fetch current time to show in message
            _, current_time = await db.get_media_delete_config(chat_id)
            return await message.reply_text(f"🔛 **Media Auto-Delete is ON.**\n⏱ Current Delay: `{current_time} seconds`")

        # B. HANDLE TIME SETTING (Value + Unit)
        # Expected: /setdelay 10 s
        if len(message.command) < 3:
            return await message.reply_text("⚠️ Unit batana zaroori hai. Ex: `/setdelay 30 s`")

        try:
            value = int(arg1)
            unit = message.command[2].lower()
        except ValueError:
            return await message.reply_text("❌ Value number honi chahiye.")

        # Calculate Seconds
        seconds = 0
        if unit.startswith("s"): # seconds
            seconds = value
        elif unit.startswith("m"): # minutes
            seconds = value * 60
        elif unit.startswith("h"): # hours
            seconds = value * 3600
        else:
            return await message.reply_text("❌ Invalid Unit! Use `s`, `m`, or `h`.")

        # Constraints (Max 24h = 86400s)
        if seconds > 86400:
            return await message.reply_text("❌ Maximum delay is **24 Hours**.")
        if seconds < 5:
             return await message.reply_text("❌ Minimum delay is **5 Seconds**.")

        # Save to DB
        await db.set_media_delete_config(chat_id, seconds)
        await message.reply_text(f"✅ **Set!** All media will auto-delete after **{seconds} seconds**.")


    # --- 2. MEDIA WATCHER & DELETER ---
    # Filters.media includes: Photo, Video, Sticker, Animation, Audio, Voice, Document
    @app.on_message(filters.media & filters.group, group=2)
    async def media_auto_deleter(client, message: Message):
        
        # Check if Enabled
        is_enabled, delay_time = await db.get_media_delete_config(message.chat.id)
        
        if not is_enabled:
            return

        # Wait for the delay
        await asyncio.sleep(delay_time)

        # Delete
        try:
            await message.delete()
        except Exception:
            pass # Message might be already deleted or permission lost
          
