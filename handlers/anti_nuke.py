import time
import logging
from pyrogram import Client, filters
from pyrogram.types import ChatMemberUpdated, ChatPrivileges, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus

from config import OWNER_ID, BOT_USERNAME
import db

# Limit: 3 Actions in 60 seconds (Testing ke liye)
VELOCITY_LIMIT = 3
TIME_FRAME = 60

FLOOD_CACHE = {}

def register_anti_nuke(app: Client):

    # --- HELPER: Whitelist Check ---
    async def is_whitelisted(chat_id: int, user_id: int) -> bool:
        if user_id == OWNER_ID:
            print(f"🛡️ Ignoring Action: Actor {user_id} is OWNER.")
            return True
        if await db.is_user_whitelisted(chat_id, user_id):
            print(f"🛡️ Ignoring Action: Actor {user_id} is Whitelisted.")
            return True
        return False

    # --- HELPER: Speed Check ---
    async def check_velocity(chat_id: int, user_id: int) -> bool:
        current_time = time.time()
        
        if chat_id not in FLOOD_CACHE:
            FLOOD_CACHE[chat_id] = {}
        if user_id not in FLOOD_CACHE[chat_id]:
            FLOOD_CACHE[chat_id][user_id] = []

        # Purana data saaf karo
        FLOOD_CACHE[chat_id][user_id] = [
            t for t in FLOOD_CACHE[chat_id][user_id] 
            if current_time - t < TIME_FRAME
        ]

        # Naya action add karo
        FLOOD_CACHE[chat_id][user_id].append(current_time)
        
        count = len(FLOOD_CACHE[chat_id][user_id])
        print(f"⚠️ Anti-Nuke Trace: User {user_id} Count: {count}/{VELOCITY_LIMIT}")

        if count > VELOCITY_LIMIT:
            FLOOD_CACHE[chat_id][user_id] = [] 
            return True
        
        return False

    # --- PUNISHMENT LOGIC (With Error Reporting) ---
    async def punish_hacker(client: Client, chat_id: int, user, reason: str):
        try:
            print(f"🚨 ATTEMPTING TO DEMOTE: {user.first_name}")
            
            # 1. Try to Demote
            no_rights = ChatPrivileges(
                can_manage_chat=False,
                can_delete_messages=False,
                can_manage_video_chats=False,
                can_restrict_members=False,
                can_promote_members=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False,
                can_post_messages=False,
                can_edit_messages=False,
                is_anonymous=False
            )

            await client.promote_chat_member(
                chat_id=chat_id,
                user_id=user.id,
                privileges=no_rights
            )

            # 2. If Successful, Send Alert
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 View Admin", url=f"tg://user?id={user.id}")]
            ])

            await client.send_message(
                chat_id, 
                f"🚨 **ANTI-NUKE TRIGGERED** 🚨\n\n"
                f"👮‍♂️ **Admin:** {user.mention}\n"
                f"🛑 **Action:** {reason}\n"
                f"✅ **Result:** Demoted Successfully.\n",
                reply_markup=buttons
            )

        except Exception as e:
            # 3. IF FAILED -> TELL THE USER WHY
            error_msg = str(e)
            print(f"❌ DEMOTE FAILED: {error_msg}")
            
            readable_error = "Unknown Error"
            if "RIGHTS_NOT_ENOUGH" in error_msg:
                readable_error = "Mera Rank kam hai! Main is Admin ko demote nahi kar sakta (Telegram Restriction)."
            elif "USER_ADMIN_INVALID" in error_msg:
                readable_error = "Main Owner ke banaye hue Admin ko remove nahi kar sakta."

            await client.send_message(
                chat_id,
                f"⚠️ **Anti-Nuke Alert**\n\n"
                f"I detected mass-action by {user.mention}, BUT I failed to demote them.\n"
                f"**Reason:** `{readable_error}`\n"
                f"**Technical:** `{error_msg}`"
            )

    # --- MAIN WATCHER ---
    @app.on_chat_member_updated(filters.group)
    async def anti_nuke_watcher(client, update: ChatMemberUpdated):
        chat = update.chat
        
        if not update.from_user:
            return
        actor = update.from_user
        
        # Safe Users check
        if actor.id == client.me.id:
            return
        if await is_whitelisted(chat.id, actor.id):
            return

        old = update.old_chat_member.status if update.old_chat_member else ChatMemberStatus.LEFT
        new = update.new_chat_member.status if update.new_chat_member else ChatMemberStatus.LEFT
        
        action_detected = False
        action_type = ""

        # Case A: Kick/Ban (Member -> Left/Banned)
        if old in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.RESTRICTED] and \
           new in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
            
            # Agar Actor != Target (Matlab kisi ne nikala)
            target = update.new_chat_member.user
            if actor.id != target.id:
                action_detected = True
                action_type = "Mass Kick/Ban"

        # Case B: Promotion
        if old not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER] and \
           new in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            
            action_detected = True
            action_type = "Mass Promotion"
            
            if update.new_chat_member.user.is_bot:
                await punish_hacker(client, chat.id, actor, "Adding/Promoting Bots")
                return

        if action_detected:
            if await check_velocity(chat.id, actor.id):
                await punish_hacker(client, chat.id, actor, action_type)
                
