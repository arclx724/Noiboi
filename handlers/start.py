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
    # 1. SEND START MENU
    # ==========================================================
    async def send_start_menu(message, user, is_edit=False):
        # Yahan formatting rehne di hai kyunki ye crash nahi karta
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

        if is_edit:
            await message.edit_media(media=InputMediaPhoto(media=START_IMAGE, caption=text), reply_markup=buttons)
        else:
            await message.reply_photo(START_IMAGE, caption=text, reply_markup=buttons)

    # ==========================================================
    # 2. SEND HELP MENU
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
                InlineKeyboardButton("Greetings", callback_data="greetings"),
                InlineKeyboardButton("Clean Service", callback_data="Clean-Service"),
                InlineKeyboardButton("Anti NSFW", callback_data="anti-nsfw"),
            ],
            [
                InlineKeyboardButton("Locks", callback_data="locks"),
                InlineKeyboardButton("Media Guardian", callback_data="Media-Guardian"),
                InlineKeyboardButton("No Bots", callback_data="No-Bots"),
            ],
            [InlineKeyboardButton("Moderation", callback_data="moderation")],
            [InlineKeyboardButton("Anti Cheater", callback_data="anti-cheater")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
        ])

        if is_edit:
            await message.edit_media(media=InputMediaPhoto(media=START_IMAGE, caption=text), reply_markup=buttons)
        else:
            await message.reply_photo(START_IMAGE, caption=text, reply_markup=buttons)

    # ==========================================================
    # 3. START COMMAND
    # ==========================================================
    @app.on_message(filters.private & filters.command("start"))
    async def start_command(client, message):
        user = message.from_user
        await db.add_user(user.id, user.first_name)
        
        # Deep Link Check
        if len(message.command) > 1 and message.command[1] == "help":
            await send_help_menu(message, is_edit=False)
            return

        # Normal Start
        await send_start_menu(message, user, is_edit=False)

    # ==========================================================
    # 4. CALLBACKS
    # ==========================================================
    @app.on_callback_query(filters.regex("help"))
    async def help_callback(client, callback_query):
        await send_help_menu(callback_query.message, is_edit=True)
        await callback_query.answer()

    @app.on_callback_query(filters.regex("back_to_start"))
    async def back_to_start_callback(client, callback_query):
        user = callback_query.from_user
        await send_start_menu(callback_query.message, user, is_edit=True)
        await callback_query.answer()

    # --- Feature Callbacks (FIXED: ALL MARKDOWN REMOVED TO PREVENT CRASH) ---
    @app.on_callback_query(filters.regex("greetings"))
    async def greetings_callback(client, callback_query):
        text = "⚙ Welcome System\n\n- /setwelcome <text>\n- /welcome on/off"
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help")]])
        await callback_query.message.edit_media(media=InputMediaPhoto(media=START_IMAGE, caption=text), reply_markup=buttons)
        await callback_query.answer()

    @app.on_callback_query(filters.regex("locks"))
    async def locks_callback(client, callback_query):
        text = "🔐 **Lock System Guide**\n\n**Commands:**\n- `/lock` <type>: Lock a specific feature.\n- `/unlock` <type>: Unlock a specific feature.\n- `/locks`: View current group settings.\n\n**Available Types:**\n`url`, `sticker`, `media`, `username`, `forward`\n\n**Example:**\n`/lock url` → Blocks all links.\n`/unlock sticker` → Allows stickers again.\n\n⚠️ **Note:** Admins are not affected by these locks."
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help")]])
        await callback_query.message.edit_media(media=InputMediaPhoto(media=START_IMAGE, caption=text), reply_markup=buttons)
        await callback_query.answer()

    @app.on_callback_query(filters.regex("Media-Guardian"))
    async def media_callback(client, callback_query):
        text = "**Set auto-delete delay media using:**\n\n `/setdelay on/off`\n `/setdelay` <value> [s/m/h]\n\n **Examples:**\n `/setdelay 10 s` → `10 seconds`\n `/setdelay 5 m`  → 5 minutes\n `/setdelay 1 h`  → 1 hour (max 24h)"
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help")]])
        await callback_query.message.edit_media(media=InputMediaPhoto(media=START_IMAGE, caption=text), reply_markup=buttons)
        await callback_query.answer()

    @app.on_callback_query(filters.regex("No-Bots"))
    async def bots_callback(client, callback_query):
        text = "🤖 No Bots System\n\n- Protect your group from users who invite spam bots.\n `/nobots on` - Disable users to invite spam bots.\n- `/nobots off` - Enable users to invite spam bots."
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help")]])
        await callback_query.message.edit_media(media=InputMediaPhoto(media=START_IMAGE, caption=text), reply_markup=buttons)
        await callback_query.answer()

    @app.on_callback_query(filters.regex("anti-nsfw"))
    async def nsfw_callback(client, callback_query):
        # NOTE: Hum yahan Markdown (**) use kar rahe hain, HTML (<b>) nahi.
        text = (
            "🔞 **Smart Anti-NSFW System**\n\n"
            "This system uses advanced AI to detect and auto-delete Nudity, Gore, and Violence from your group.\n"
            "It scans **Photos, Stickers, and Video Thumbnails** instantly.\n\n"
            "**👮‍♂️ Admin Commands:**\n"
            "• `/antinsfw on` - Enable protection.\n"
            "• `/antinsfw off` - Disable protection.\n\n"
            "**🔑 API Management (Sudo Only):**\n"
            "• `/addapi <user> <secret>` - Add your API Key (Sudo Only).\n"
            #"• `/addamthy <user> <secret>` - Donate an API Key (Public).\n"
            "• `/checkapi` - Check active keys & remaining scans (Sudo Only).\n\n"
        )
            #"ℹ️ _The bot automatically rotates keys and removes expired ones._"
        
        
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help")]])
        
        # 'parse_mode' ko explicitly Markdown set karein taaki confusion na ho
        from pyrogram.enums import ParseMode
        await callback_query.message.edit_media(
            media=InputMediaPhoto(media=START_IMAGE, caption=text, parse_mode=ParseMode.MARKDOWN), 
            reply_markup=buttons
        )
        await callback_query.answer()

    @app.on_callback_query(filters.regex("moderation"))
    async def moderation_callback(client, callback_query):
        text = "👮‍♂️ **Moderation**\n\n- /kick: Kick a user.\n- /ban: Ban a user.\n- /mute: Mute a user.\n- /promote: Promote a user.\n- /demote: Demote a user."
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help")]])
        await callback_query.message.edit_media(media=InputMediaPhoto(media=START_IMAGE, caption=text), reply_markup=buttons)
        await callback_query.answer()

    @app.on_callback_query(filters.regex("Clean-Service"))
    async def clean_service_callback(client, callback_query):
        # Backticks removed here: `/command` -> /command
        text = "🧹 **Clean Service**\n\n- `/noevents on/off`: Filter 'X joined or left the group' notifications.\n- `/nolinks on/off`: Filter messages with links, mentions, forwards, or reply markup.\n- `/noforwards on/off`: Filter messages with a mention of any participants.\n- `/nocontacts on/off`: Filter messages with contact numbers of users.\n- `/nolocations on/off`: Filter messages containing user locations.\n- `/nocommands on/off`: Filter commands from group members.\n- `/nohashtags on/off`: Filter messages containing hashtags.\n- `/antiflood on/off`: Limit frequent messages (3 per 20 seconds)."
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help")]])
        await callback_query.message.edit_media(media=InputMediaPhoto(media=START_IMAGE, caption=text), reply_markup=buttons)
        await callback_query.answer()

    @app.on_callback_query(filters.regex("anti-cheater"))
    async def anti_cheater_callback(client, callback_query):
        text = "**Anti-Cheater**\n\n - Works automatically — no commands needed\n\n 🚨 **The bot tracks admin actions.**\n - If an admin kicks or bans more than 10 users in 24 hours, they are auto-demoted.\n\n - Limits reset automatically every 24 hours.\n\n 🔒 **Only admins promoted by this bot can be auto-demoted.**\n Use /promote and give the bot Add Admin permission.\n\n 🛡️ Protects your group from fake or abusive admins."
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

                await message.reply_photo(START_IMAGE, caption=text, reply_markup=buttons)

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
        
