import time
import logging
from pyrogram import Client, filters
from pyrogram.types import ChatMemberUpdated, ChatPrivileges, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus

from config import OWNER_ID, BOT_USERNAME
import db

# ================= CONFIGURATION =================
# Ab Limit kam kar di hai testing ke liye:
# 3 Actions in 60 Seconds -> Trigger
VELOCITY_LIMIT = 3
TIME_FRAME = 60

# In-Memory Cache
FLOOD_CACHE = {}

logger = logging.getLogger(__name__)

def register_anti_nuke(app: Client):

    # ================= HELPERS =================

    async def is_whitelisted(chat_id: int, user_id: int) -> bool:
        if user_id == OWNER_ID:
            return True
        if await db.is_user_whitelisted(chat_id, user_id):
            return True
        return False

    async def check_velocity(chat_id: int, user_id: int) -> bool:
        current_time = time.time()
        
        if chat_id not in FLOOD_CACHE:
            FLOOD_CACHE[chat_id] = {}
        if user_id not in FLOOD_CACHE[chat_id]:
            FLOOD_CACHE[chat_id][user_id] = []

        # Purane actions hatao (Clean up)
        FLOOD_CACHE[chat_id][user_id] = [
            t for t in FLOOD_CACHE[chat_id][user_id] 
            if current_time - t < TIME_FRAME
        ]

        # Naya action jodo
        FLOOD_CACHE[chat_id][user_id].append(current_time)
        
        count = len(FLOOD_CACHE[chat_id][user_id])
        print(f"⚠️ Security Log: User {user_id} Action Count: {count}/{VELOCITY_LIMIT}") # DEBUG LOG

        if count > VELOCITY_LIMIT:
            FLOOD_CACHE[chat_id][user_id] = [] # Reset after punishment
            return True
        
        return False

    async def punish_hacker(client: Client, chat_id: int, user, reason: str):
        try:
            print(f"🚨 PUNISHING: {user.first_name} for {reason}") # DEBUG LOG
            
            # Demote immediately
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

            # Alert Message
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 View Admin", url=f"tg://user?id={user.id}")]
            ])

            await client.send_message(
                chat_id, 
                f"🚨 **SECURITY ALERT** 🚨\n\n"
                f"👮‍♂️ **Admin:** {user.mention}\n"
                f"🛑 **Action:** {reason}\n"
                f"⚡ **Penalty:** Demoted Immediately.\n"
                f"⚠️ *Limit exceeded (>{VELOCITY_LIMIT} actions)*",
                reply_markup=buttons
            )

        except Exception as e:
            print(f"❌ Failed to punish: {e}")

    # ================= WATCHER LOGIC =================

    @app.on_chat_member_updated(filters.group)
    async def anti_nuke_watcher(client, update: ChatMemberUpdated):
        chat = update.chat
        
        # Actor woh hai jisne action liya (Admin)
        if not update.from_user:
            return
        actor = update.from_user
        
        # Target woh hai jiske saath action hua (Member)
        target = update.new_chat_member.user

        # 1. Ignore Safe Users (Bot, Owner, Whitelisted)
        if actor.id == client.me.id or actor.id == OWNER_ID:
            return
        if await is_whitelisted(chat.id, actor.id):
            return

        # Status check
        old = update.old_chat_member.status if update.old_chat_member else ChatMemberStatus.LEFT
        new = update.new_chat_member.status if update.new_chat_member else ChatMemberStatus.LEFT
        
        action_detected = False
        action_type = ""

        # --- DETECTION LOGIC ---

        # Case A: KICK (Remove from Group) or BAN
        # Agar purana status Member/Admin/Restricted tha -> Aur naya Left/Banned hai
        if old in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.RESTRICTED] and \
           new in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
            
            # IMP: Agar User ne khud leave kiya, toh Actor ID == Target ID hoga.
            # Agar Actor != Target, iska matlab kisi ne nikala hai (Kick/Ban).
            if actor.id != target.id:
                action_detected = True
                action_type = "Mass Kick/Ban"
                print(f"👀 Kick Detected by {actor.first_name}")

        # Case B: PROMOTION (Admin banana)
        if old not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER] and \
           new in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            
            action_detected = True
            action_type = "Mass Promotion"
            
            # Bot Promotion check (Strict Rule)
            if target.is_bot:
                await punish_hacker(client, chat.id, actor, "Adding/Promoting Bots")
                return

        # --- EXECUTION ---
        if action_detected:
            # Check Speed
            if await check_velocity(chat.id, actor.id):
                await punish_hacker(client, chat.id, actor, action_type)



