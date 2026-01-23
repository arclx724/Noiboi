import time
from pyrogram import Client, filters
from pyrogram.types import ChatMemberUpdated, ChatPrivileges
from pyrogram.enums import ChatMemberStatus

# ================= CONFIGURATION =================
# Testing Limit: Sirf 3 kicks par action lega
LIMIT = 3
TIME_FRAME = 60 # 60 Seconds

# Temporary Memory (RAM)
TRAFFIC = {}

async def demote_admin(client, chat_id, user_id, user_name):
    """Admin ko demote karne ka function"""
    try:
        await client.send_message(chat_id, f"⚡ **ATTEMPTING TO DEMOTE:** {user_name}")
        
        # Demote Logic
        await client.promote_chat_member(
            chat_id,
            user_id,
            privileges=ChatPrivileges(can_manage_chat=False) # Sab Rights False
        )
        await client.send_message(chat_id, f"✅ **SUCCESS:** {user_name} has been Demoted!")
        
    except Exception as e:
        await client.send_message(chat_id, f"❌ **FAIL:** Demote nahi kar paya!\nError: `{e}`")

def register_anti_nuke(app: Client):

    @app.on_chat_member_updated(filters.group)
    async def debug_nuke_watcher(client, update: ChatMemberUpdated):
        """
        Ye function har member update par chalega aur check karega.
        """
        chat = update.chat
        
        # 1. Actor Check (Jisne action liya)
        if not update.from_user:
            return
        actor = update.from_user
        target = update.new_chat_member.user

        # 2. Ignore Bot Itself
        if actor.id == client.me.id:
            return

        # 3. KICK DETECTION LOGIC
        # Purana Status kya tha?
        old_status = update.old_chat_member.status if update.old_chat_member else ChatMemberStatus.LEFT
        # Naya Status kya hai?
        new_status = update.new_chat_member.status if update.new_chat_member else ChatMemberStatus.LEFT

        # Agar banda group se gaya hai (LEFT ya BANNED)
        if new_status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
            
            # Agar Actor aur Target alag hain -> Matlab Kick/Ban hua hai
            if actor.id != target.id:
                
                # --- VELOCITY CHECK (RAM) ---
                current_time = time.time()
                
                # Data structure initialize karo
                if chat.id not in TRAFFIC:
                    TRAFFIC[chat.id] = {}
                if actor.id not in TRAFFIC[chat.id]:
                    TRAFFIC[chat.id][actor.id] = []
                
                # Naya kick time add karo
                TRAFFIC[chat.id][actor.id].append(current_time)
                
                # Purane actions (jo 60 sec se pehle the) hata do
                TRAFFIC[chat.id][actor.id] = [t for t in TRAFFIC[chat.id][actor.id] if current_time - t < TIME_FRAME]
                
                count = len(TRAFFIC[chat.id][actor.id])
                
                # 📢 DEBUG MESSAGE (Group mein dikhega)
                # await client.send_message(
                #     chat.id, 
                #     f"👀 **Monitor:** {actor.first_name} removed {target.first_name}.\n"
                #     f"🔢 Count: {count}/{LIMIT}"
                # )
                
                print(f"DEBUG: {actor.first_name} did action {count}/{LIMIT}")

                # ACTION TIME
                if count >= LIMIT:
                    await client.send_message(chat.id, f"🚨 **LIMIT CROSS!** {actor.first_name} is nuking!")
                    await demote_admin(client, chat.id, actor.id, actor.first_name)
                    # Reset count
                    TRAFFIC[chat.id][actor.id] = []

