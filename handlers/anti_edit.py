import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_USERNAME, SUPPORT_GROUP
import db

def register_antiedit_handlers(app: Client):

    # Note: Hum 'on_edited_message' use kar rahe hain
    @app.on_edited_message(filters.group)
    async def anti_edit_watcher(client, message):
        chat_id = message.chat.id
        
        # 1. Check: Feature Enabled hai ya nahi?
        if not await db.is_antiedit_enabled(chat_id):
            return

        # 2. Strict Mode: No Admin/Owner Checks (Sabke liye delete hoga)
        # Humne yahan permission check skip kar diya hai.

        # 3. Send Warning Message
        text = (
            f"⚠️ **Anti-Edit Warning**\n\n"
            f"Hey {message.from_user.mention}, editing messages is strictly prohibited here!\n"
            f"⏳ **Your message will be auto-deleted in 60 seconds.**"
        )
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("Add Me To Your Group 🎉", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")],
            [InlineKeyboardButton("⌂ Support ⌂", url=SUPPORT_GROUP)]
        ])

        try:
            # Warning Bhejo
            warning_msg = await message.reply_text(text, reply_markup=buttons)

            # 4. Wait for 60 Seconds
            await asyncio.sleep(60)

            # 5. Delete Messages (User's + Bot's Warning)
            await message.delete()      # User ka message delete
            await warning_msg.delete()  # Bot ka warning delete

        except Exception as e:
            # Agar message pehle hi delete ho gaya ho to crash na ho
            pass
          
