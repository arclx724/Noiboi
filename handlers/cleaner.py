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
        user = await client.get_chat_member(message.chat.id, message.from_user.id)
        if user.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return

        if len(message.command) > 1:
            arg = message.command[1].lower()
            if arg == "on":
                await db.set_nocommands_status(message.chat.id, True)
                await message.reply_text("🔇 **No-Commands Enabled!**\nUsers won't be able to use commands.")
            elif arg == "off":
                await db.set_nocommands_status(message.chat.id, False)
                await message.reply_text("🔊 **No-Commands Disabled!**")
        else:
            await message.reply_text("Usage: `/nocommands on` or `/nocommands off`")

    # --- /noevents on/off ---
    @app.on_message(filters.command("noevents") & filters.group)
    async def noevents_switch(client, message):
        user = await client.get_chat_member(message.chat.id, message.from_user.id)
        if user.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return

        if len(message.command) > 1:
            arg = message.command[1].lower()
            if arg == "on":
                await db.set_noevents_status(message.chat.id, True)
                await message.reply_text("👻 **No-Events Enabled!**\nJoin/Left messages will be deleted.")
            elif arg == "off":
                await db.set_noevents_status(message.chat.id, False)
                await message.reply_text("👋 **No-Events Disabled!**")
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
                pass

    # --- Delete User Commands (Starts with /) ---
    # Note: Hum commands ko filter kar rahe hain jo '/' se start hote hain
    @app.on_message(filters.text & filters.group, group=21)
    async def delete_user_commands(client, message):
        # Check agar message command hai (starts with / or ! or .)
        if not message.text or not message.text.startswith(("/", "!", ".")):
            return

        # Check agar feature ON hai
        if not await db.is_nocommands_enabled(message.chat.id):
            return

        # Check agar user Admin hai (Admins should be allowed)
        try:
            member = await client.get_chat_member(message.chat.id, message.from_user.id)
            if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                return # Admin hai, ignore karo
        except:
            pass

        # Agar normal user hai, to delete karo
        try:
            await message.delete()
        except:
            pass

