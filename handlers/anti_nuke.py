import time
import logging
from pyrogram import Client, filters
from pyrogram.types import ChatMemberUpdated, ChatPrivileges, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus

from config import OWNER_ID, BOT_USERNAME
import db

# ================= CONFIGURATION =================
# Limit: 6 actions in 120 seconds (2 minutes)
VELOCITY_LIMIT = 6
TIME_FRAME = 120 

# In-Memory Cache for Velocity Checks (Super Fast)
# Format: { chat_id: { user_id: [timestamp1, timestamp2, ...] } }
FLOOD_CACHE = {}

logger = logging.getLogger(__name__)

def register_anti_nuke(app: Client):

    # ================= HELPERS =================

    async def is_whitelisted(chat_id: int, user_id: int) -> bool:
        # 1. Check Owner
        if user_id == OWNER_ID:
            return True
        # 2. Check Database Whitelist (Trust Users)
        if await db.is_user_whitelisted(chat_id, user_id):
            return True
        return False

    async def check_velocity(chat_id: int, user_id: int) -> bool:
        """
        Returns True if limit exceeded (NUKE DETECTED), False otherwise.
        """
        current_time = time.time()
        
        # Initialize structure
        if chat_id not in FLOOD_CACHE:
            FLOOD_CACHE[chat_id] = {}
        if user_id not in FLOOD_CACHE[chat_id]:
            FLOOD_CACHE[chat_id][user_id] = []

        # Filter out old timestamps (older than 2 mins)
        # We keep only actions that happened in the last TIME_FRAME
        FLOOD_CACHE[chat_id][user_id] = [
            t for t in FLOOD_CACHE[chat_id][user_id] 
            if current_time - t < TIME_FRAME
        ]

        # Add new action timestamp
        FLOOD_CACHE[chat_id][user_id].append(current_time)

        # Check count
        if len(FLOOD_CACHE[chat_id][user_id]) > VELOCITY_LIMIT:
            # Clear cache for this user to prevent spamming alerts
            FLOOD_CACHE[chat_id][user_id] = []
            return True
        
        return False

    async def punish_hacker(client: Client, chat_id: int, user, reason: str):
        """
        Strip admin rights immediately and announce.
        """
        try:
            # Demote: Set all permissions to False
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

            # Apply Demotion
            await client.promote_chat_member(
                chat_id=chat_id,
                user_id=user.id,
                privileges=no_rights
            )

            # Send Alert
            alert_text = (
                f"🚨 **SECURITY ALERT: ANTI-NUKE** 🚨\n\n"
                f"👮‍♂️ **Admin:** {user.mention}\n"
                f"🛑 **Action:** {reason}\n"
                f"⚡ **Penalty:** Admin Rights Stripped.\n\n"
                f"⚠️ *The user exceeded safety limits (Velocity Check).*"
            )
            
            # Button to check
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 View Admin", url=f"tg://user?id={user.id}")]
            ])

            await client.send_message(chat_id, alert_text, reply_markup=buttons)
            logger.warning(f"ANTI-NUKE: Demoted {user.id} in {chat_id} for {reason}")

        except Exception as e:
            logger.error(f"Failed to punish user {user.id}: {e}")

    # ================= WATCHER LOGIC =================

    @app.on_chat_member_updated(filters.group)
    async def anti_nuke_watcher(client, update: ChatMemberUpdated):
        """
        Watches for:
        1. Mass Kicks/Bans
        2. Mass Promotions
        3. Bot Promotions
        """
        chat = update.chat
        
        # Ensure we have the 'actor' (Who did the action)
        if not update.from_user:
            return

        actor = update.from_user
        
        # --- 1. IGNORE SAFE USERS ---
        # Owner, Bot itself, and Whitelisted users are immune
        if actor.id == client.me.id:
            return
        if await is_whitelisted(chat.id, actor.id):
            return

        # --- 2. DETECT ACTION TYPE ---
        
        is_ban_kick = False
        is_promote = False
        is_bot_promote = False

        # Status transitions
        old_status = update.old_chat_member.status if update.old_chat_member else ChatMemberStatus.LEFT
        new_status = update.new_chat_member.status if update.new_chat_member else ChatMemberStatus.LEFT

        # A. KICK / BAN DETECTION
        # If user was a member/admin and is now BANNED or LEFT (and actor is not the user themselves)
        if (old_status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR] and
            new_status in [ChatMemberStatus.BANNED, ChatMemberStatus.LEFT]):
            
            # If actor.id != new_chat_member.user.id, it means someone else kicked them.
            if actor.id != update.new_chat_member.user.id:
                is_ban_kick = True

        # B. PROMOTION DETECTION
        # If user was not admin, and is now ADMIN/OWNER
        if (old_status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER] and
            new_status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]):
            
            is_promote = True
            
            # SPECIAL RULE: Bot Promotion
            if update.new_chat_member.user.is_bot:
                is_bot_promote = True

        # --- 3. APPLY RULES ---

        # RULE 1: Never Promote a Bot (Instant Strike)
        if is_bot_promote:
            await punish_hacker(client, chat.id, actor, "Promoting a Bot (Unauthorized)")
            # Also demote the bot they added
            try:
                await client.promote_chat_member(
                    chat.id, 
                    update.new_chat_member.user.id, 
                    ChatPrivileges(can_manage_chat=False) # No rights
                )
            except:
                pass
            return

        # RULE 2: Velocity Check (Mass Ban/Kick/Promote)
        if is_ban_kick or is_promote:
            # Check Speed
            limit_exceeded = await check_velocity(chat.id, actor.id)
            
            if limit_exceeded:
                action_type = "Mass Kicking/Banning" if is_ban_kick else "Mass Promoting"
                await punish_hacker(client, chat.id, actor, f"{action_type} (> {VELOCITY_LIMIT} actions)")


