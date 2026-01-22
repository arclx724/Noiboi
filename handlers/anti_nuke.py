import time
from pyrogram import Client, filters
from pyrogram.types import ChatMemberUpdated, ChatPrivileges
from pyrogram.enums import ChatMemberStatus

from config import OWNER_ID
import db  # must have: is_user_whitelisted(chat_id, user_id)

# ================= CONFIG =================

BAN_LIMIT = 10
TIME_FRAME = 86400  # 24 hours (in seconds)

FLOOD_CACHE = {}

# ================= HELPERS =================

async def is_whitelisted(chat_id: int, user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    if await db.is_user_whitelisted(chat_id, user_id):
        return True
    return False


async def check_ban_velocity(chat_id: int, user_id: int) -> bool:
    now = time.time()

    FLOOD_CACHE.setdefault(chat_id, {})
    FLOOD_CACHE[chat_id].setdefault(user_id, [])

    # Keep only last 24h
    FLOOD_CACHE[chat_id][user_id] = [
        t for t in FLOOD_CACHE[chat_id][user_id]
        if now - t < TIME_FRAME
    ]

    FLOOD_CACHE[chat_id][user_id].append(now)

    count = len(FLOOD_CACHE[chat_id][user_id])
    print(f"🚨 BAN COUNT | User {user_id}: {count}/{BAN_LIMIT}")

    return count >= BAN_LIMIT


async def punish_hacker(client: Client, chat_id: int, user, reason: str):
    try:
        me = await client.get_chat_member(chat_id, client.me.id)

        if not me.privileges or not me.privileges.can_promote_members:
            print("❌ Bot has no demotion rights")
            return

        await client.promote_chat_member(
            chat_id=chat_id,
            user_id=user.id,
            privileges=ChatPrivileges(
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
        )

        await client.send_message(
            chat_id,
            f"🚨 **ANTI-NUKE ACTIVATED** 🚨\n\n"
            f"👮 **Admin:** {user.mention}\n"
            f"🛑 **Reason:** {reason}\n"
            f"✅ **Action:** Admin Demoted Automatically"
        )

    except Exception as e:
        await client.send_message(
            chat_id,
            f"⚠️ **ANTI-NUKE FAILED**\n\n"
            f"Admin: {user.mention}\n"
            f"Error: `{e}`"
        )

# ================= MAIN WATCHER =================

def register_anti_nuke(app: Client):

    @app.on_chat_member_updated(filters.group)
    async def anti_nuke_watcher(client: Client, update: ChatMemberUpdated):

        chat = update.chat
        actor = update.from_user

        if not actor:
            return
        if actor.id == client.me.id:
            return
        if await is_whitelisted(chat.id, actor.id):
            return

        old = update.old_chat_member
        new = update.new_chat_member

        if not old or not new:
            return

        target = new.user
        if not target:
            return

        # ================= BAN / KICK DETECTION =================
        # Member/Admin -> Not a member = Ban/Kick
        if old.is_member and not new.is_member:
            if actor.id == target.id:
                return  # self leave

            exceeded = await check_ban_velocity(chat.id, actor.id)
            if exceeded:
                await punish_hacker(
                    client,
                    chat.id,
                    actor,
                    "Mass bans detected (10 bans in 24 hours)"
                )
