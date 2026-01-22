import time
from pyrogram import Client, filters
from pyrogram.types import ChatMemberUpdated, ChatPrivileges, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus
from config import OWNER_ID, BOT_USERNAME
import db

# Config: Ek din mein max kitne users ko kick/ban/promote kar sakte hain
DAILY_LIMIT = 10 

async def punish_nuker(client, chat_id, user, count):
    """
    Hacker ko Demote karega
    """
    try:
        # Demote immediately
        await client.promote_chat_member(
            chat_id,
            user.id,
            privileges=ChatPrivileges(can_manage_chat=False) # Sab rights cheen lo
        )
        
        # Alert Message
        await client.send_message(
            chat_id,
            f"🚨 **ANTI-NUKE TRIGGERED**\n\n"
            f"👮‍♂️ **Admin:** {user.mention}\n"
            f"🛑 **Status:** Demoted Successfully.\n"
            f"⚠️ **Reason:** Crossed daily limit ({count}/{DAILY_LIMIT})"
        )
    except Exception as e:
        print(f"Failed to punish {user.first_name}: {e}")


def register_anti_nuke(app: Client):

    # --- WATCHER: Kicks, Bans & Promotions ---
    @app.on_chat_member_updated(filters.group)
    async def limit_watcher(client, update: ChatMemberUpdated):
        chat = update.chat
        
        # Actor = Jisne action liya (Admin)
        if not update.from_user:
            return
        actor = update.from_user
        
        # 1. Ignore Safe Users (Owner & Bot)
        if actor.id == client.me.id or actor.id == OWNER_ID:
            return

        # 2. Check Action Type
        old = update.old_chat_member.status if update.old_chat_member else ChatMemberStatus.LEFT
        new = update.new_chat_member.status if update.new_chat_member else ChatMemberStatus.LEFT
        
        action_detected = False
        
        # Case A: Kick/Ban (Member -> Left/Banned)
        if old in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR] and \
           new in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
            # Agar Actor != Target (Matlab kisi ne nikala)
            if actor.id != update.new_chat_member.user.id:
                action_detected = True

        # Case B: Promotion (Member -> Admin)
        elif old not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER] and \
             new in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            action_detected = True

        # 3. Check Database Limit
        if action_detected:
            is_allowed, current_count = await db.check_admin_limit(chat.id, actor.id, DAILY_LIMIT)
            
            # Debug Print (Terminal mein dikhega)
            print(f"🛡️ Security: {actor.first_name} Action {current_count}/{DAILY_LIMIT}")

            if not is_allowed:
                # Limit Cross -> Demote!
                await punish_nuker(client, chat.id, actor, current_count)

    # --- COMMAND: Reset Limits (Owner Only) ---
    @app.on_message(filters.command("resetlimits") & filters.group)
    async def reset_limits_cmd(client, message):
        user = await client.get_chat_member(message.chat.id, message.from_user.id)
        
        if user.status != ChatMemberStatus.OWNER and message.from_user.id != OWNER_ID:
            return await message.reply_text("❌ Sirf Group Owner limits reset kar sakta hai.")
            
        await db.reset_admin_limit(message.chat.id)
        await message.reply_text("✅ **Success:** All admin limits have been reset for this group.")

