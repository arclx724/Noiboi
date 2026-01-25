# ============================================================
# Group Manager Bot
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
# Start Message Logic
# ==========================================================
    async def send_start_menu(message, user):
        # user yahan object hona chahiye taaki .mention kaam kare
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

        if message.text:
            await message.reply_photo(START_IMAGE, caption=text, reply_markup=buttons)
        else:
            media = InputMediaPhoto(media=START_IMAGE, caption=text)
            await message.edit_media(media=media, reply_markup=buttons)

# ==========================================================
# Start Command (Fixed Indentation & User Object)
# ==========================================================
    @app.on_message(filters.private & filters.command("start"))
    async def start_command(client, message):
        user = message.from_user
        await db.add_user(user.id, user.first_name)
        # Sahi: Pura 'user' object bhejein
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
# Callbacks
# ==========================================================
    @app.on_callback_query(filters.regex("help"))
    async def help_callback(client, callback_query):
        await send_help_menu(callback_query.message)
        await callback_query.answer()

    @app.on_callback_query(filters.regex("back_to_start"))
    async def back_to_start_callback(client, callback_query):
        # FIX: Yahan user object bhejna zaroori hai
        user = callback_query.from_user
        await send_start_menu(callback_query.message, user)
        await callback_query.answer()

    @app.on_callback_query(filters.regex("greetings"))
    async def greetings_callback(client, callback_query):
        text = """
╔══════════════════╗
    ⚙ Welcome System
╚══════════════════╝

Commands to Manage Welcome Messages:

- /setwelcome <text> : Set a custom welcome message
- /welcome on        : Enable welcome messages
- /welcome off       : Disable welcome messages

Supported Placeholders:
- {username}, {first_name}, {id}, {mention}
"""
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help")]])
        media = InputMediaPhoto(media=START_IMAGE, caption=text)
        await callback_query.message.edit_media(media=media, reply_markup=buttons)
        await callback_query.answer()

    @app.on_callback_query(filters.regex("locks"))
    async def locks_callback(client, callback_query):
        text = """
╔══════════════════╗
     ⚙ Locks System
╚══════════════════╝

- /lock <type>    : Enable a lock
- /unlock <type>  : Disable a lock
- /locks          : Show active locks

Types: url, sticker, media, username, etc.
"""
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help")]])
        media = InputMediaPhoto(media=START_IMAGE, caption=text)
        await callback_query.message.edit_media(media=media, reply_markup=buttons)
        await callback_query.answer()

    @app.on_callback_query(filters.regex("moderation"))
    async def moderation_callback(client, callback_query):
        text = """
╔══════════════════╗
      ⚙️ Moderation
╚══════════════════╝

- /kick, /ban, /mute, /warn
- /promote, /demote
"""
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help")]])
        media = InputMediaPhoto(media=START_IMAGE, caption=text)
        await callback_query.message.edit_media(media=media, reply_markup=buttons)
        await callback_query.answer()

    @app.on_callback_query(filters.regex("Clean-Service"))
    async def clean_service_callback(client, callback_query):
        text = "Clean up service messages like join/leave.\nCommands: /cleanservice, /keepservice"
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help")]])
        media = InputMediaPhoto(media=START_IMAGE, caption=text)
        await callback_query.message.edit_media(media=media, reply_markup=buttons)
        await callback_query.answer()

    @app.on_callback_query(filters.regex("anti-cheater"))
    async def anti_cheater_callback(client, callback_query):
        text = "🛡️ Anti-Cheater System\n\nAutomatically demotes admins who kick/ban too many users."
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help")]])
        media = InputMediaPhoto(media=START_IMAGE, caption=text)
        await callback_query.message.edit_media(media=media, reply_markup=buttons)
        await callback_query.answer()

# ==========================================================
# Owner Commands
# ==========================================================
    @app.on_message(filters.private & filters.command("broadcast"))
    async def broadcast_message(client, message):
        if message.from_user.id != OWNER_ID: return
        if not message.reply_to_message: return await message.reply_text("Reply to a message.")
        
        users = await db.get_all_users()
        sent = 0
        for user_id in users:
            try:
                await client.send_message(user_id, message.reply_to_message.text)
                sent += 1
            except: pass
        await message.reply_text(f"✅ Broadcast finished! Sent to {sent} users.")

    @app.on_message(filters.private & filters.command("stats"))
    async def stats_command(client, message):
        if message.from_user.id != OWNER_ID: return
        users = await db.get_all_users()
        await message.reply_text(f"💡 Total users: {len(users)}")
        
