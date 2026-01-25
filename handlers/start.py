# ============================================================
#Group Manager Bot
# Author: LearningBotsOfficial (https://github.com/LearningBotsOfficial) 
# Support: https://t.me/LearningBotsCommunity
# Channel: https://t.me/learning_bots
# YouTube: https://youtube.com/@learning_bots
# License: Open-source (keep credits, no resale)
# ============================================================


from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto
)
from config import BOT_USERNAME, SUPPORT_GROUP, UPDATE_CHANNEL, START_IMAGE, OWNER_ID
import db

def register_handlers(app: Client):

# ==========================================================
# Start Message
# ==========================================================
    async def send_start_menu(message, user):
        text = f"""

   ✨ Hello {user.mention}! ✨

👋 I am Mini Aadi 

Highlights:
─────────────────────────────
- Smart Anti-Spam & Link Shield
- Adaptive Lock System (URLs, Media, Language & more)
- Modular & Scalable Protection
- Sleek UI with Inline Controls

» More New Features coming soon ...
"""

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚒️ Add to Group ⚒️", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")],
            [
                InlineKeyboardButton("⌂ Support ⌂", url=SUPPORT_GROUP),
                InlineKeyboardButton("⌂ Update ⌂", url=UPDATE_CHANNEL),
            ],
            [
                InlineKeyboardButton("※ ŎŴɳēŔ ※", url=f"tg://user?id={OWNER_ID}"),
                InlineKeyboardButton("Repo", url="https://t.me/RoboKaty"),
                
            ],
            [InlineKeyboardButton("📚 Help Commands 📚", callback_data="help")]
        ])

        # If /start command, send a new photo
        if message.text:
            await message.reply_photo(START_IMAGE, caption=text, reply_markup=buttons)
        else:
            # If callback, edit the same message
            media = InputMediaPhoto(media=START_IMAGE, caption=text)
            await message.edit_media(media=media, reply_markup=buttons)

# ==========================================================
# Start Command
# ==========================================================
    @app.on_message(filters.private & filters.command("start"))
async def start_command(client, message):
    user = message.from_user
    await db.add_user(user.id, user.first_name)
    
    # ❌ Galat: await send_start_menu(message, user.first_name)
    # ✅ Sahi: Pura 'user' object bhejein
    await send_start_menu(message, user) 

# ==========================================================
# Help Menu Message
# ==========================================================
    async def send_help_menu(message):
        text = """
╔══════════════════╗
     Help Menu
╚══════════════════╝

Choose a category below to explore commands:
─────────────────────────────
"""
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⌂ Greetings ⌂", callback_data="greetings"),
                InlineKeyboardButton("⌂ Clean Service ⌂", callback_data="Clean-Service"),
                InlineKeyboardButton("⌂ Locks ⌂", callback_data="locks"),
            ],
            [
                InlineKeyboardButton("⌂ Moderation ⌂", callback_data="moderation")
            ],
            [
                InlineKeyboardButton("⌂ Anti-Cheater ⌂", callback_data="anti-cheater")
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
        ])

        media = InputMediaPhoto(media=START_IMAGE, caption=text)
        await message.edit_media(media=media, reply_markup=buttons)

# ==========================================================
# Help Callback_query
# ==========================================================
    @app.on_callback_query(filters.regex("help"))
    async def help_callback(client, callback_query):
        await send_help_menu(callback_query.message)
        await callback_query.answer()

# ==========================================================
# back to start Callback_query
# ==========================================================
    @app.on_callback_query(filters.regex("back_to_start"))
    async def back_to_start_callback(client, callback_query):
        user = callback_query.from_user.first_name
        await send_start_menu(callback_query.message, user)
        await callback_query.answer()

# ==========================================================
# Greetings Callback_query
# ==========================================================
    @app.on_callback_query(filters.regex("greetings"))
    async def greetings_callback(client, callback_query):
        text = """
╔══════════════════╗
    ⚙ Welcome System
╚══════════════════╝

Commands to Manage Welcome Messages:

- /setwelcome <text> : Set a custom welcome message for your group
- /welcome on        : Enable the welcome messages
- /welcome off       : Disable the welcome messages

Supported Placeholders:
- {username} : Telegram username
- {first_name} : User's first name
- {id} : User ID
- {mention} : Mention user in message

Example:
 /setwelcome Hello {first_name}! Welcome to {title}!
"""
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="help")]
        ])
        media = InputMediaPhoto(media=START_IMAGE, caption=text)
        await callback_query.message.edit_media(media=media, reply_markup=buttons)
        await callback_query.answer()

# ==========================================================
# Clean Service Callback_query
# ==========================================================
    @app.on_callback_query(filters.regex("Clean-Service"))
    async def clean_service_callback(client, callback_query):
        text = """
**Clean Service**

Clean up automated telegram service messages! The available categories are:
- all: All service messages.
- join: When a new user joins, or is added. eg: 'X joined the chat'
- leave: When a user leaves, or is removed. eg: 'X left the chat'
- other: Miscellaneous items; such as chat boosts, successful telegram payments, proximity alerts, webapp messages, message auto deletion changes, or checklist updates.
- photo: When chat photos or chat backgrounds are changed.
- pin: When a new message is pinned. eg: 'X pinned a message'
- title: When chat or topic titles are changed.
- videochat: When a video chat action occurs - eg starting, ending, scheduling, or adding members to the call.

Admin commands:
- /cleanservice <type/yes/no/on/off>: Select which service messages to delete.
- /keepservice <type>: Select which service messages to stop deleting.
- /nocleanservice <type>: (same as keepservice)
- /cleanservicetypes: List all the available service messages, with a brief explanation.

Examples:
- Stop all telegram service messages:
-> /cleanservice all

- Stop telegrams 'x joined the chat' messages:
-> /cleanservice join

- Keep telegrams 'x pinned a message' messages:
-> /keepservice pin
"""
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="help")]
        ])

        try:
            # Pehle purana photo wala message delete karein
            await callback_query.message.delete()
            
            # Ab naya text message bhejein (Isme 4096 char limit milti hai)
            await client.send_message(
                chat_id=callback_query.message.chat.id,
                text=text,
                reply_markup=buttons
            )
        except Exception as e:
            # Agar delete nahi ho paya toh purane tarike se edit try karein
            await callback_query.edit_message_text(text=text, reply_markup=buttons)
            
        await callback_query.answer()
        
# ==========================================================
# Locks callback_query
# ==========================================================
    @app.on_callback_query(filters.regex("locks"))
    async def locks_callback(client, callback_query):
        text = """
╔══════════════════╗
     ⚙ Locks System
╚══════════════════╝

Commands to Manage Locks:

- /lock <type>    : Enable a lock for the group
- /unlock <type>  : Disable a lock for the group
- /locks          : Show currently active locks

Available Lock Types:
- url       : Block links
- sticker   : Block stickers
- media     : Block photos/videos/gifs
- username  : Block messages with @username mentions
- language  : Block non-English messages

Example:
 /lock url       : Blocks any messages containing links
 /unlock sticker : Allows stickers again
"""
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="help")]
        ])
        media = InputMediaPhoto(media=START_IMAGE, caption=text)
        await callback_query.message.edit_media(media=media, reply_markup=buttons)
        await callback_query.answer()

# ==========================================================
# Moderation Callback_query
# ==========================================================
    @app.on_callback_query(filters.regex("moderation"))
    async def info_callback(client, callback_query):
        try:
            text = """
╔══════════════════╗
      ⚙️ Moderation System
╚══════════════════╝

Manage your group easily with these tools:

¤ /kick <user> — Remove a user  
¤ /ban <user> — Ban permanently  
¤ /unban <user> — Lift ban  
¤ /mute <user> — Disable messages  
¤ /unmute <user> — Allow messages again  
¤ /warn <user> — Add warning (3 = mute)  
¤ /warns <user> — View warnings  
¤ /resetwarns <user> — Clear all warnings  
¤ /promote <user> — make admin
¤ /demote <user> — remove from admin  

💡 Example:
Reply to a user or type  
<code>/ban @username</code>

"""
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="help")]
            ])
    
            media = InputMediaPhoto(media=START_IMAGE, caption=text)
            await callback_query.message.edit_media(media=media, reply_markup=buttons)
            await callback_query.answer()
    
        except Exception as e:
            print(f"Error in info_callback: {e}")
            await callback_query.answer("❌ Something went wrong.", show_alert=True)


# ==========================================================
# Clean-Service Callback_query
# ==========================================================
    @app.on_callback_query(filters.regex("Clean-Service"))
    async def info_callback(client, callback_query):
        try:
            text = """
Clean Service

Clean up automated telegram service messages! The available categories are:
- all: All service messages.
- join: When a new user joins, or is added. eg: 'X joined the chat'
- leave: When a user leaves, or is removed. eg: 'X left the chat'
- other: Miscellaneous items; such as chat boosts, successful telegram payments, proximity alerts, webapp messages, message auto deletion changes, or checklist updates.
- photo: When chat photos or chat backgrounds are changed.
- pin: When a new message is pinned. eg: 'X pinned a message'
- title: When chat or topic titles are changed.
- videochat: When a video chat action occurs - eg starting, ending, scheduling, or adding members to the call.

Admin commands:
- /cleanservice <type/yes/no/on/off>: Select which service messages to delete.
- /keepservice <type>: Select which service messages to stop deleting.
- /nocleanservice <type>: (same as keepservice)
- /cleanservicetypes: List all the available service messages, with a brief explanation.

Examples:
- Stop all telegram service messages:
-> /cleanservice all

- Stop telegrams 'x joined the chat' messages:
-> /cleanservice join

- Keep telegrams 'x pinned a message' messages:
-> /keepservice pin</code>

"""
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="help")]
            ])
    
            media = InputMediaPhoto(media=START_IMAGE, caption=text)
            await callback_query.message.edit_media(media=media, reply_markup=buttons)
            await callback_query.answer()
    
        except Exception as e:
            print(f"Error in info_callback: {e}")
            await callback_query.answer("❌ Something went wrong.", show_alert=True)
    
# ==========================================================
# Anti-Cheater Callback_query
# ==========================================================
    @app.on_callback_query(filters.regex("anti-cheater"))
    async def info_callback(client, callback_query):
        try:
            text = """
╔══════════════════╗  
    👮 Anti-Cheater ꜱʏꜱᴛᴇᴍ  
╚══════════════════╝  

- Works automatically — no commands needed

🚨 The bot tracks admin actions.
- If an admin kicks or bans more than 10 users in 24 hours, they are auto‑demoted.

- Limits reset automatically every 24 hours.

🔒 Only admins promoted by this bot can be auto‑demoted.
Use /promote and give the bot Add Admin permission.

🛡️ Protects your group from fake or abusive admins.</code>

"""
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="help")]
            ])
    
            media = InputMediaPhoto(media=START_IMAGE, caption=text)
            await callback_query.message.edit_media(media=media, reply_markup=buttons)
            await callback_query.answer()
    
        except Exception as e:
            print(f"Error in info_callback: {e}")
            await callback_query.answer("❌ Something went wrong.", show_alert=True)
    

# ==========================================================
# Broadcast Command
# ==========================================================
    @app.on_message(filters.private & filters.command("broadcast"))
    async def broadcast_message(client, message):
        if not message.reply_to_message:
            await message.reply_text("⚠️ Please reply to a message to broadcast it.")
            return

        if message.from_user.id != OWNER_ID:
            await message.reply_text("❌ Only the bot owner can use this command.")
            return

        text_to_send = message.reply_to_message.text or message.reply_to_message.caption
        if not text_to_send:
            await message.reply_text("⚠️ The replied message has no text to send.")
            return

        users = await db.get_all_users()
        sent, failed = 0, 0

        await message.reply_text(f"Broadcasting to {len(users)} users..")

        for user_id in users:
            try:
                await client.send_message(user_id, text_to_send)
                sent += 1
            except Exception:
                failed += 1

        await message.reply_text(f"✅ Broadcast finished!\n\n Sent: {sent}\nFailed: {failed}")

# ==========================================================
# stats Command
# ==========================================================
    @app.on_message(filters.private & filters.command("stats"))
    async def stats_command(client, message):
        if message.from_user.id != OWNER_ID:
            return await message.reply_text("❌ Only the bot owner can use this command")

        users = await db.get_all_users()
        return await message.reply_text(f"💡 Total users: {len(users)}")
