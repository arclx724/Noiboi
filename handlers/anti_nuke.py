
import time
from pyrogram import Client, filters
from pyrogram.types import ChatMemberUpdated, ChatPrivileges
from pyrogram.enums import ChatMemberStatus

# ================= CONFIGURATION =================
# Testing ke liye Limit = 3 rakho
LIMIT = 3
TIME_FRAME = 60 

# RAM Cache
TRAFFIC = {}

async def demote_admin(client, chat_id, user_id, user_name):
    """Admin ko demote karne ka function"""
    try:
        await client.send_message(chat_id, f"⚡ **ANTI-NUKE:** Demoting {user_name}...")
        
        # Demote Logic
        await client.promote_chat_member(
            chat_id,
            user_id,
            privileges=ChatPrivileges(can_manage_chat=False) # Sab rights cheen lo
        )
        await client.send_message(chat_id, f"✅ **SUCCESS:** {user_name} Demoted!")
        
    except Exception as e:
        await client.send_message(chat_id, f"❌ **FAIL:** Error: `{e}`")

def register_anti_nuke(app: Client):

    # --- 🛠 TEST COMMAND ---
    @app.on_message(filters.command("trydemote") & filters.group)
    async def test_demote(client, message):
        if not message.reply_to_message:
            return await message.reply("❌ Reply karke command do.")
        target = message.reply_to_message.from_user
        await demote_admin(client, message.chat.id, target.id, target.first_name)

    # --- 🛡️ MAIN WATCHER (Priority Group 5) ---
    # Group=5 ka matlab hai ye sabse alag chalega, koi isse rok nahi payega
    @app.on_chat_member_updated(filters.group, group=5)
    async def nuclear_watcher(client, update: ChatMemberUpdated):
        chat = update.chat
        
        if not update.from_user:
            return
        actor = update.from_user
        target = update.new_chat_member.user

        # Sirf Bot ko ignore karo, Owner ko bhi pakdo (Testing ke liye)
        if actor.id == client.me.id:
            return

        # ACTION DETECTION
        old = update.old_chat_member.status if update.old_chat_member else ChatMemberStatus.LEFT
        new = update.new_chat_member.status if update.new_chat_member else ChatMemberStatus.LEFT

        # KICK/BAN Check
        if new in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
            
            # Agar Actor ne khud leave nahi kiya (Kisi ne nikala hai)
            if actor.id != target.id:
                
                # --- TRAFFIC CHECK ---
                current_time = time.time()
                
                if chat.id not in TRAFFIC:
                    TRAFFIC[chat.id] = {}
                if actor.id not in TRAFFIC[chat.id]:
                    TRAFFIC[chat.id][actor.id] = []
                
                TRAFFIC[chat.id][actor.id].append(current_time)
                
                # 60 sec purane actions hatao
                TRAFFIC[chat.id][actor.id] = [t for t in TRAFFIC[chat.id][actor.id] if current_time - t < TIME_FRAME]
                
                count = len(TRAFFIC[chat.id][actor.id])
                
                # 📢 DEBUG: Ye line confirm karegi ki code chal raha hai
                print(f"DEBUG: {actor.first_name} Kicked Someone. Count: {count}/{LIMIT}")
                
                # LIMIT CROSS
                if count >= LIMIT:
                    await client.send_message(chat.id, f"🚨 **NUKE DETECTED!** {actor.first_name} crossed limit!")
                    await demote_admin(client, chat.id, actor.id, actor.first_name)
                    TRAFFIC[chat.id][actor.id] = [] # Reset
