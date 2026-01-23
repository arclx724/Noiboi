import time
from pyrogram import Client, filters
from pyrogram.types import ChatMemberUpdated, ChatPrivileges
from pyrogram.enums import ChatMemberStatus
from config import OWNER_ID

# ================= CONFIGURATION =================
# Testing ke liye Limit = 1 rakho taaki turant pakde
LIMIT = 1 
TIME_FRAME = 60 

# RAM Cache
TRAFFIC = {}

async def demote_admin(client, chat_id, user_id, user_name):
    """Admin ko demote karne ki koshish karega aur result batayega"""
    try:
        await client.send_message(chat_id, f"⚡ **ATTEMPTING TO DEMOTE:** {user_name}...")
        
        # Demote Logic (Sab rights FALSE kar do)
        await client.promote_chat_member(
            chat_id,
            user_id,
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
        await client.send_message(chat_id, f"✅ **SUCCESS:** {user_name} ko Demote kar diya!")
        return True
        
    except Exception as e:
        error_msg = str(e)
        reason = "Unknown Error"
        
        if "USER_ADMIN_INVALID" in error_msg:
            reason = "⚠️ **HIERARCHY ERROR:** Main is Admin ko remove nahi kar sakta kyunki isse **Owner** ya **Mujhse Bade Admin** ne banaya hai.\n\n👉 **Solution:** Is Admin ko Bot ke through promote karo."
        elif "RIGHTS_NOT_ENOUGH" in error_msg:
            reason = "⚠️ **PERMISSION ERROR:** Mere paas 'Add New Admins' ki permission nahi hai."
            
        await client.send_message(chat_id, f"❌ **FAILED:** Demote nahi hua!\n**Reason:** {reason}\n**Technical:** `{error_msg}`")
        return False

def register_anti_nuke(app: Client):

    # --- 🛠 TEST COMMAND (Isse Power Check Karo) ---
    @app.on_message(filters.command("trydemote") & filters.group)
    async def test_demote(client, message):
        # Sirf Owner use kare
        # if message.from_user.id != OWNER_ID:
        #    return await message.reply("Sirf Owner ye check kar sakta hai.")

        if not message.reply_to_message:
            return await message.reply("❌ Kisi Admin ke message par reply karke `/trydemote` likho.")
            
        target = message.reply_to_message.from_user
        await demote_admin(client, message.chat.id, target.id, target.first_name)


    # --- 🛡️ MAIN WATCHER ---
    @app.on_chat_member_updated(filters.group)
    async def debug_nuke_watcher(client, update: ChatMemberUpdated):
        chat = update.chat
        
        if not update.from_user:
            return
        actor = update.from_user
        target = update.new_chat_member.user

        # Ignore Bot
        if actor.id == client.me.id:
            return

        # ACTION DETECTION (Kick/Ban)
        old = update.old_chat_member.status if update.old_chat_member else ChatMemberStatus.LEFT
        new = update.new_chat_member.status if update.new_chat_member else ChatMemberStatus.LEFT

        # Agar Kick/Ban hua hai
        if new in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
            
            # Agar Actor ne khud leave nahi kiya (Kisi ne nikala hai)
            if actor.id != target.id:
                
                # --- VELOCITY CHECK (RAM) ---
                current_time = time.time()
                
                if chat.id not in TRAFFIC:
                    TRAFFIC[chat.id] = {}
                if actor.id not in TRAFFIC[chat.id]:
                    TRAFFIC[chat.id][actor.id] = []
                
                # Action count karo
                TRAFFIC[chat.id][actor.id].append(current_time)
                
                # Purana data saaf karo (60 sec window)
                TRAFFIC[chat.id][actor.id] = [t for t in TRAFFIC[chat.id][actor.id] if current_time - t < TIME_FRAME]
                
                count = len(TRAFFIC[chat.id][actor.id])
                
                # 📢 DEBUG: Har Kick par message aayega
                await client.send_message(chat.id, f"👀 **Monitor:** {actor.first_name} removed a member. (Count: {count}/{LIMIT})")

                # LIMIT CROSS
                if count >= LIMIT:
                    await client.send_message(chat.id, f"🚨 **LIMIT REACHED!** Nuke detected by {actor.first_name}")
                    await demote_admin(client, chat.id, actor.id, actor.first_name)
                    TRAFFIC[chat.id][actor.id] = [] # Reset
