from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus
import db

def register_cleaner_handlers(app: Client):

    # ======================================================
    # 1. COMMANDS TO ENABLE/DISABLE
    # ======================================================

    # --- /nocommands on/off ---
    @app.on_message(filters.command("nocommands") & filters.group)
    async def nocommands_switch(client, message):
        chat_id = message.chat.id
        user_id = message.from_user.id

        # 1. Check if User is Admin
        member = await client.get_chat_member(chat_id, user_id)
        if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            await message.reply_text("❌ **Access Denied!**\nSirf Admins ye command use kar sakte hain.")
            return

        if len(message.command) > 1:
            arg = message.command[1].lower()
            
            if arg == "on":
                # 2. Check if Bot has Delete Rights (Before Enabling)
                bot_member = await client.get_chat_member(chat_id, client.me.id)
                if not bot_member.privileges or not bot_member.privileges.can_delete_messages:
                    await message.reply_text("⚠️ **Error:** Mere paas **Delete Messages** ka right nahi hai!\nPlease mujhe Admin banao aur Delete permission do tabhi ye feature kaam karega.")
                    return

                await db.set_nocommands_status(chat_id, True)
                await message.reply_text("🔇 **No-Commands Enabled!**\nAb normal members commands use nahi kar payenge (Auto-Delete).")
            
            elif arg == "off":
                await db.set_nocommands_status(chat_id, False)
                await message.reply_text("🔊 **No-Commands Disabled!**\nSabhi members commands use kar sakte hain.")
            else:
                await message.reply_text("Usage: `/nocommands on` or `/nocommands off`")
        else:
            await message.reply_text("Usage: `/nocommands on` or `/nocommands off`")

    # --- /noevents on/off ---
    @app.on_message(filters.command("noevents") & filters.group)
    async def noevents_switch(client, message):
        chat_id = message.chat.id
        user_id = message.from_user.id

        # 1. Check if User is Admin
        member = await client.get_chat_member(chat_id, user_id)
        if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            await message.reply_text("❌ **Access Denied!**\nSirf Admins ye command use kar sakte hain.")
            return

        if len(message.command) > 1:
            arg = message.command[1].lower()
            
            if arg == "on":
                # 2. Check if Bot has Delete Rights
                bot_member = await client.get_chat_member(chat_id, client.me.id)
                if not bot_member.privileges or not bot_member.privileges.can_delete_messages:
                    await message.reply_text("⚠️ **Error:** Mere paas **Delete Messages** ka right nahi hai!\nPlease mujhe Admin banao aur Delete permission do.")
                    return

                await db.set_noevents_status(chat_id, True)
                await message.reply_text("👻 **No-Events Enabled!**\nJoin/Left notifications ab delete kar diye jayenge.")
            
            elif arg == "off":
                await db.set_noevents_status(chat_id, False)
                await message.reply_text("👋 **No-Events Disabled!**\nJoin/Left notifications ab dikhenge.")
            else:
                await message.reply_text("Usage: `/noevents on` or `/noevents off`")
        else:
            await message.reply_text("Usage: `/noevents on` or `/noevents off`")

    # ======================================================
    # 2. WATCHERS (REAL ACTION)
    # ======================================================

    # --- Delete Service Messages (Join/Left) ---
    @app.on_message(filters.service & filters.group, group=20)
    async def delete_service_messages(client, message):
        if await db.is_noevents_enabled(message.chat.id):
            try:
                await message.delete()
            except:
                # Agar delete fail ho jaye (Rights lost), to hum chup rahenge
                # Kyunki baar baar error bhejna spam hoga
                pass

    # --- Delete User Commands (Starts with /, !, .) ---
    @app.on_message(filters.text & filters.group, group=21)
    async def delete_user_commands(client, message):
        # Filter commands
        if not message.text or not message.text.startswith(("/", "!", ".")):
            return

        # Check Settings
        if not await db.is_nocommands_enabled(message.chat.id):
            return

        # Allow Admins
        try:
            member = await client.get_chat_member(message.chat.id, message.from_user.id)
            if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                return 
        except:
            pass

        # Delete for Normal Users
        try:
            await message.delete()
        except:
            pass
            
