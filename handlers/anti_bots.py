from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus
import db

def register_antibot_handlers(app: Client):

    # --- 1. CONFIGURATION COMMAND (/nobots) ---
    @app.on_message(filters.command("nobots") & filters.group)
    async def antibot_config(client, message: Message):
        chat_id = message.chat.id
        user_id = message.from_user.id
        
        # --- PERMISSION CHECK ---
        member = await client.get_chat_member(chat_id, user_id)
        
        if member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
             return await message.reply_text("❌ Only Admins can use this.")
        
        # Special Rights Check (Change Info & Add Admins)
        if member.status == ChatMemberStatus.ADMINISTRATOR:
             privileges = member.privileges
             if not (privileges.can_change_info and privileges.can_promote_members):
                 return await message.reply_text("❌ You need **Change Group Info** & **Add New Admins** rights to toggle this.")
        
        # --- ARGUMENT CHECK ---
        if len(message.command) < 2:
            return await message.reply_text("⚠️ Usage: `/nobots on` or `/nobots off`")
            
        action = message.command[1].lower()
        
        if action in ["on", "enable", "yes"]:
            await db.set_antibot_status(chat_id, True)
            await message.reply_text("🤖 **Anti-Bot System Enabled.**\nOnly Admins with **'Add New Admins'** permission can add bots.")
            
        elif action in ["off", "disable", "no"]:
            await db.set_antibot_status(chat_id, False)
            await message.reply_text("🤖 **Anti-Bot System Disabled.**")
        else:
            await message.reply_text("⚠️ Invalid option. Use `on` or `off`.")


    # --- 2. BOT WATCHER (The Guard) ---
    @app.on_message(filters.new_chat_members & filters.group, group=3)
    async def antibot_watcher(client, message: Message):
        chat_id = message.chat.id
        
        # Check if Protection is ON
        if not await db.is_antibot_enabled(chat_id):
            return

        # Check who added the members
        adder = message.from_user
        if not adder:
            return # Unknown source
            
        # --- CHECK ADDER'S RIGHTS ---
        # Kya adder authorized hai? (Owner ya Admin with 'Add New Admins' right)
        is_authorized = False
        
        adder_member = await client.get_chat_member(chat_id, adder.id)
        
        if adder_member.status == ChatMemberStatus.OWNER:
            is_authorized = True
        elif adder_member.status == ChatMemberStatus.ADMINISTRATOR:
            if adder_member.privileges.can_promote_members: # "Add New Admins" right
                is_authorized = True
        
        # Agar adder authorized hai, toh bots allow karo
        if is_authorized:
            return

        # --- CHECK & REMOVE UNAUTHORIZED BOTS ---
        for member in message.new_chat_members:
            if member.is_bot:
                try:
                    # 1. Bot ko Nikalo (Ban/Kick)
                    await client.ban_chat_member(chat_id, member.id)
                    
                    # 2. Inform karo
                    await message.reply_text(
                        f"🛡️ **Anti-Bot Action**\n"
                        f"🗑️ Removed: {member.mention}\n"
                        f"⚠️ Reason: {adder.mention} does not have 'Add New Admins' permission."
                    )
                except Exception as e:
                    # Agar Bot ke paas kick karne ki power na ho
                    await message.reply_text(f"❌ Failed to remove bot {member.mention}. Make sure I am Admin!")
                  
