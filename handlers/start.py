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
    # 1. SEND START MENU (Smart Function)
    # ==========================================================
    async def send_start_menu(message, user, is_edit=False):
        text = f"""
✨ **Hey there {user.mention}!** ✨

My name is **MissKaty** 🤖. I have many useful features for you, feel free to add me to your group.

**Highlights:**
────────────────────────
• Smart Anti-Spam & Link Shield 🛡️
• Adaptive Lock System 🔒
• Modular & Scalable Protection ⚙️
• Sleek UI with Inline Controls 🚀

» More New Features coming soon ...
"""
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("Add Me To Your Group 🎉", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")],
            [
                InlineKeyboardButton("⌂ Support ⌂", url=SUPPORT_GROUP),
                InlineKeyboardButton("⌂ Update ⌂", url=UPDATE_CHANNEL),
            ],
            [
                InlineKeyboardButton("Dev 👩‍💻", url=f"tg://user?id={OWNER_ID}"),
                InlineKeyboardButton("Report Bug 🐞", url="https://t.me/RoboKaty"),
            ],
            [InlineKeyboardButton("Commands ❓", callback_data="help")]
        ])

        # Agar Edit mode hai (Callback se aaya hai)
        if is_edit:
            await message.edit_media(media=InputMediaPhoto(media=START_IMAGE, caption=text), reply_markup=buttons)
        # Agar New Message mode hai (Command se aaya hai)
        else:
            await message.reply_photo(START_IMAGE, caption=text, reply_markup=buttons)

    # ==========================================================
    # 2. SEND HELP MENU (Smart Function)
    # ==========================================================
    async def send_help_menu(message, is_edit=False):
        text = """
╔══════════════════╗
     **Help Menu** 📚
╚══════════════════╝

Choose a category below to explore commands:
─────────────────────────────
"""
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⌂ Greetings ⌂", callback_data="greetings"),
                InlineKeyboardButton("⌂ Clean Service ⌂", callback_data="Clean-Service"),
            ],
            [
                InlineKeyboardButton("⌂ Locks ⌂", callback_data="locks"),
                InlineKeyboardButton("⌂ Media Guardian ⌂", callback_data="Media-Guardian"),
                InlineKeyboardButton("⌂ No Bots ⌂", callback_data="No-Bots"),
            ],
            [InlineKeyboardButton("⌂ Moderation ⌂", callback_data="moderation")],
            [InlineKeyboardButton("⌂ Anti-Cheater ⌂", callback_data="anti-cheater")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
        ])

        # Agar Edit mode hai (Callback se aaya hai)
        if is_edit:
            await message.edit_media(media=InputMediaPhoto(media=START_IMAGE, caption=text), reply_markup=buttons)
        # Agar New Message mode hai (Command se aaya hai)
        else:
            await message.reply_photo(START_IMAGE, caption=text, reply_markup=buttons)

    # ==========================================================
    # 3. START COMMAND (Logic Fixed)
    # ==========================================================
    @app.on_message(filters.private & filters.command("start"))
    async def start_command(client, message):
        user = message.from_user
        await db.add_user(user.id, user.first_name)
        
        # --- DEEP LINK LOGIC ---
        if len(message.command) > 1 and message.command[1] == "help":
            # Yahan hum 'is_edit=False' bhej rahe hain kyunki ye Command hai
            await send_help_menu(message, is_edit=False)
            return

        # --- NORMAL START ---
        await send_start_menu(message, user, is_edit=False)

    # ==========================================================
    # 4. CALLBACK HANDLERS
    # ==========================================================
    @app.on_callback_query(filters.regex("help"))
    async def help_callback(client, callback_query):
        # Yahan hum 'is_edit=True' bhej rahe hain kyunki ye Button click hai
        await send_help_menu(callback_query.message, is_edit=True)
        await callback_query.answer()

    @app.on_callback_query(filters.regex("back_to_start"))
    async def back_to_start_callback(client, callback_query):
        user = callback_query.from_user
        await send_start_menu(callback_query.message, user, is_edit=True)
        await callback_query.answer()

    # --- Other Categories (Sab Edit Mode mein rahenge) ---
    @app.on_callback_query(filters.regex("greetings"))
    async def greetings_callback(client, callback_query):
        text = "**⚙ Welcome System**\n\n- `/setwelcome <text>`\n- `/welcome on/off`"
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help")]])
        await callback_query.message.edit_media(media=InputMediaPhoto(media=START_IMAGE, caption=text), reply_markup=buttons)
        await callback_query.answer()

    @app.on_callback_query(filters.regex("locks"))
    async def locks_callback(client, callback_query):
        text = "**⚙ Locks System**\n\n- `/lock <type>`\n- `/unlock <type>`\n- `/locks`"
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help")]])
        await callback_query.message.edit_media(media=InputMediaPhoto(media=START_IMAGE, caption=text), reply_markup=buttons)
        await callback_query.answer()

    @app.on_callback_query(filters.regex("Media-Guardian"))
    async def media_callback(client, callback_query):
        text = "**⏳ Media Auto-Delete**\n\n- `/setdelay 10 s`\n- `/setdelay off`"
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help")]])
        await callback_query.message.edit_media(media=InputMediaPhoto(media=START_IMAGE, caption=text), reply_markup=buttons)
        await callback_query.answer()

    @app.on_callback_query(filters.regex("No-Bots"))
    async def bots_callback(client, callback_query):
        text = "**🤖 No Bots System**\n\n- `/nobots on`\n- `/nobots off`"
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help")]])
        await callback_query.message.edit_media(media=InputMediaPhoto(media=START_IMAGE, caption=text), reply_markup=buttons)
        await callback_query.answer()

    @app.on_callback_query(filters.regex("moderation"))
    async def moderation_callback(client, callback_query):
        text = "**👮‍♂️ Moderation**\n\n- `/kick`, `/ban`, `/mute`\n- `/promote`, `/demote`"
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help")]])
        await callback_query.message.edit_media(media=InputMediaPhoto(media=START_IMAGE, caption=text), reply_markup=buttons)
        await callback_query.answer()

    @app.on_callback_query(filters.regex("Clean-Service"))
    async def clean_service_callback(client, callback_query):
        text = "**🧹 Clean Service**\n\n- `/cleanservice <type>`\n- `/keepservice <type>`"
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help")]])
        await callback_query.message.edit_media(media=InputMediaPhoto(media=START_IMAGE, caption=text), reply_markup=buttons)
        await callback_query.answer()

    @app.on_callback_query(filters.regex("anti-cheater"))
    async def anti_cheater_callback(client, callback_query):
        text = "**🛡️ Anti-Cheater**\n\nAutomatically demotes admins who abuse power."
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help")]])
        await callback_query.message.edit_media(media=InputMediaPhoto(media=START_IMAGE, caption=text), reply_markup=buttons)
        await callback_query.answer()

    # ==========================================================
    # 5. NEW CHAT MEMBERS (Group Welcome)
    # ==========================================================
    @app.on_message(filters.new_chat_members)
    async def welcome_bot(client, message):
        for member in message.new_chat_members:
            if member.id == client.me.id:
                text = (
                    f"🌟 ᴛʜᴀɴᴋꜱ ꜰᴏʀ ɢɪᴠɪɴɢ ᴍᴇ ᴀ ᴄʜᴀɴᴄᴇ ᴛᴏ ʜᴀɴᴅʟᴇ ʏᴏᴜʀ ɢʀᴏᴜᴘ **{message.chat.title}**! 🛡️\n\n"
                    "🛡️ ɴᴏᴡ ɪ ᴄᴀɴ sᴀᴠᴇ ʏᴏᴜʀ ɢʀᴏᴜᴘ ꜰʀᴏᴍ sᴜsᴘᴇɴsɪᴏɴ ᴀɴᴅ ᴄᴏᴘʏʀɪɢʜᴛ sᴛʀɪᴋᴇ ʙʏ ᴅᴇʟᴇᴛɪɴɢ ᴛʜᴇ ᴇᴅɪᴛᴇᴅ ᴍᴇssᴀɢᴇ.\n"
                    "🚀 ʟᴇᴛꜱ ᴍᴀᴋᴇ ᴛʜɪs ɢʀᴏᴜᴘ ᴀᴡᴇsᴏᴍᴇ ᴛᴏɢᴇᴛʜᴇʀ !!\n"
                    "🔔 ɴᴇᴇᴅ ʜᴇʟᴘ ᴊᴜsᴛ ᴄʟɪᴄᴋ ʜᴇʀᴇ 👇!!"
                )
                buttons = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Commands ❓", url=f"https://t.me/{BOT_USERNAME}?start=help")]
                ])
                await message.reply_text(text, reply_markup=buttons)

    # ==========================================================
    # 6. OWNER COMMANDS
    # ==========================================================
    @app.on_message(filters.private & filters.command("broadcast"))
    async def broadcast_message(client, message):
        if message.from_user.id != OWNER_ID: return
        if not message.reply_to_message: return await message.reply_text("Reply to a message.")
        users = await db.get_all_users()
        for user_id in users:
            try: await client.send_message(user_id, message.reply_to_message.text)
            except: pass
        await message.reply_text("✅ Broadcast Done!")

    @app.on_message(filters.private & filters.command("stats"))
    async def stats_command(client, message):
        if message.from_user.id != OWNER_ID: return
        users = await db.get_all_users()
        await message.reply_text(f"💡 Total users: {len(users)}")
        
