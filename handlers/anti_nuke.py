import time
from pyrogram import Client, filters
from pyrogram.types import ChatMemberUpdated, ChatPrivileges
from pyrogram.enums import ChatMemberStatus
from config import OWNER_ID
import db

# ================= CONFIGURATION =================
# Production Limit (Normal Use ke liye)
LIMIT = 3
TIME_FRAME = 300 

# RAM Cache
TRAFFIC = {}

async def punish_nuker(client, chat_id, user, count):
    """
    Hacker ko Demote karega
    """
    try:
        # Pehle Demote karo (Fastest Action)
        await client.promote_chat_member(
            chat_id,
            user.id,
            privileges=ChatPrivileges(can_manage_chat=False)
        )
        
        # Fir Alert bhejo
        await client.send_message(
            chat_id,
            f"🚨 **ANTI-NUKE TRIGGERED**\n\n"
            f"👮‍♂️ **Admin:** {user.mention}\n"
            f"🔢 **Action Count:** {count}/{LIMIT}\n"
            f"✅ **Penalty:** Admin Demoted Successfully."
        )
        
    except Exception as e:
        # Agar fail ho jaye (Hierarchy Issue)
        await client.send_message(
            chat_id,
            f"⚠️ **Security Alert:** Detected mass-action by {user.mention}, but I cannot demote them due to Telegram limitations (My rank is lower)."
        )

def register_anti_nuke(app: Client):

    # --- 🛡️ MAIN WATCHER (High Priority) ---
    @app.on_chat_member_updated(filters.group, group=5)
    async def nuke_watcher(client, update: ChatMemberUpdated):
        chat = update.chat
        
        # FIX 1: Safety Check for Actor
        if not update.from_user:
            return
        actor = update.from_user

        # FIX 2: Safely get Target User
        # Kabhi kabhi 'new_chat_member' None hota hai, isliye crash ho rha tha
        if update.new_chat_member:
            target = update.new_chat_member.user
        elif update.old_chat_member:
            target = update.old_chat_member.user
        else:
            return # Agar dono nahi hai to ignore karo

        # 1. SAFETY: Bot aur Owner ko ignore karo
        if actor.id == client.me.id or actor.id == OWNER_ID:
            return

        # 2. Whitelist Check (Database)
        if await db.is_user_whitelisted(chat.id, actor.id):
            return

        # ACTION DETECTION
        old = update.old_chat_member.status if update.old_chat_member else ChatMemberStatus.LEFT
        new = update.new_chat_member.status if update.new_chat_member else ChatMemberStatus.LEFT

        action_detected = False

        # Case A: Kick/Ban
        if new in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
            # Agar actor aur target alag hain (mtlb kisi ne kick kiya)
            if actor.id != target.id:
                action_detected = True

        # Case B: Mass Promotion (Optional)
        elif old not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER] and \
             new in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
             action_detected = True

        # 3. TRAFFIC CHECK
        if action_detected:
            current_time = time.time()
            
            if chat.id not in TRAFFIC:
                TRAFFIC[chat.id] = {}
            if actor.id not in TRAFFIC[chat.id]:
                TRAFFIC[chat.id][actor.id] = []
            
            TRAFFIC[chat.id][actor.id].append(current_time)
            
            # Clean old actions
            TRAFFIC[chat.id][actor.id] = [t for t in TRAFFIC[chat.id][actor.id] if current_time - t < TIME_FRAME]
            
            count = len(TRAFFIC[chat.id][actor.id])
            
            if count >= LIMIT:
                await punish_nuker(client, chat.id, actor, count)
                TRAFFIC[chat.id][actor.id] = [] # Reset after punishment
