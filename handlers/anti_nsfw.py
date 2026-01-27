import os
import io
import asyncio
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus
from config import BOT_USERNAME, SUPPORT_GROUP, OWNER_ID
import db

# SightEngine URL
API_URL = "https://api.sightengine.com/1.0/check.json"

def register_antinsfw_handlers(app: Client):

    # ======================================================
    # 1. OWNER COMMANDS (Manage APIs)
    # ======================================================

    @app.on_message(filters.command("addapi") & filters.private)
    async def add_nsfw_api_cmd(client, message):
        # --- DEBUG CHECK ---
        # Agar user Owner nahi hai, to usko batao (Taaki confusion na ho)
        if message.from_user.id != int(OWNER_ID):
            await message.reply_text(f"❌ **Access Denied!**\nYou are not the Owner.\n\nYour ID: `{message.from_user.id}`\nOwner ID in Config: `{OWNER_ID}`")
            return
        
        # Format: /addapi <user> <secret>
        if len(message.command) != 3:
            await message.reply_text("Usage: `/addapi <api_user> <api_secret>`")
            return
        
        api_user = message.command[1]
        api_secret = message.command[2]
        
        await db.add_nsfw_api(api_user, api_secret)
        await message.reply_text(f"✅ **API Added Successfully!**\nUser: `{api_user}`\nSecret: `******`")

    @app.on_message(filters.command("checkapi") & filters.private)
    async def check_api_stats(client, message):
        if message.from_user.id != int(OWNER_ID):
            return
        
        count = await db.get_all_nsfw_apis_count()
        await message.reply_text(f"📊 **Total Active SightEngine APIs:** `{count}`")

    # ======================================================
    # 2. GROUP ADMIN COMMANDS (On/Off)
    # ======================================================

    @app.on_message(filters.command("antinsfw") & filters.group)
    async def antinsfw_switch(client, message):
        user = await client.get_chat_member(message.chat.id, message.from_user.id)
        if user.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            await message.reply_text("❌ Access Denied! Only Admins can change this.")
            return

        if len(message.command) > 1:
            arg = message.command[1].lower()
            if arg == "on":
                await db.set_antinsfw_status(message.chat.id, True)
                await message.reply_text("🔞 **Anti-NSFW System Enabled!**\nPhotos, Stickers, and Videos (Thumbnails) will be scanned.")
            elif arg == "off":
                await db.set_antinsfw_status(message.chat.id, False)
                await message.reply_text("😌 **Anti-NSFW System Disabled!**")
        else:
            await message.reply_text("Usage: `/antinsfw on` or `/antinsfw off`")

    # ======================================================
    # 3. SCANNER LOGIC (The Core)
    # ======================================================

    async def scan_image(image_bytes):
        """Recursively try APIs until success or empty"""
        api_data = await db.get_nsfw_api()
        
        if not api_data:
            return None # No APIs left

        data = aiohttp.FormData()
        data.add_field('models', 'nudity,wad,gore')
        data.add_field('api_user', api_data['api_user'])
        data.add_field('api_secret', api_data['api_secret'])
        data.add_field('media', image_bytes, filename='image.jpg')

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL, data=data) as resp:
                    result = await resp.json()
            
            # Check for API Errors (Limit Exceeded)
            if result['status'] == 'failure':
                error_code = result.get('error', {}).get('code')
                # Code 21 = Rate Limit, Code 23 = Monthly Limit, 103 = Invalid
                if error_code in [21, 23, 103]: 
                    # Remove bad API and retry
                    await db.remove_nsfw_api(api_data['api_user'])
                    return await scan_image(image_bytes) # Retry with next key
                return None
            
            return result
            
        except Exception as e:
            return None

    @app.on_message(filters.group & (filters.photo | filters.video | filters.sticker | filters.document | filters.animation), group=35)
    async def nsfw_watcher(client, message):
        chat_id = message.chat.id
        
        # 1. Check Feature Enabled
        if not await db.is_antinsfw_enabled(chat_id):
            return

        # 2. Extract Media (Thumbnail Strategy)
        media = None
        
        if message.photo:
            media = message.photo
        elif message.sticker:
            if message.sticker.thumbs:
                media = message.sticker.thumbs[0]
            elif not message.sticker.is_animated and not message.sticker.is_video:
                media = message.sticker
        elif message.video:
            if message.video.thumbs:
                media = message.video.thumbs[0]
        elif message.animation: # GIF
            if message.animation.thumbs:
                media = message.animation.thumbs[0]
        elif message.document and "image" in message.document.mime_type:
            media = message.document

        if not media:
            return # Scan layak kuch nahi mila

        # 3. Download to RAM (BytesIO)
        try:
            # Sirf 2MB se choti file/thumb hi download karo to save RAM
            if media.file_size > 2 * 1024 * 1024: 
                return 

            file_stream = io.BytesIO()
            await client.download_media(media.file_id, file_ref=media.file_ref, file_name=file_stream)
            file_stream.seek(0) # Reset pointer
            
            # 4. Send to SightEngine
            result = await scan_image(file_stream)
            
            if not result:
                return # API error or empty

            # 5. Check Score (Threshold > 0.60 aka 60%)
            nsfw_score = 0
            
            # Nudity Check
            if 'nudity' in result:
                # Raw, Safe, Partial. We check unsafe categories.
                raw = result['nudity'].get('raw', 0)
                partial = result['nudity'].get('partial', 0)
                nsfw_score = max(raw, partial)
            
            # Weapon/Gore Check
            if 'weapon' in result and result['weapon'] > 0.8:
                nsfw_score = max(nsfw_score, result['weapon'])
            if 'gore' in result and result['gore'] > 0.8:
                nsfw_score = max(nsfw_score, result['gore'])

            # 6. ACTION: If NSFW Detected
            if nsfw_score > 0.60: # 60% se zyada NSFW
                percent = int(nsfw_score * 100)
                
                # Delete Message
                try: await message.delete()
                except: pass # Rights issue
                
                # Warning Message
                text = (
                    f"⚠️ **NSFW Content Detected!**\n"
                    f"Hey {message.from_user.mention}, your message contained {percent}% NSFW content (Nudity/Violence).\n"
                    f"It has been deleted to protect this group.\n\n"
                    f"⏳ **This warning will auto-delete in 60 seconds.**"
                )
                
                buttons = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Add Me To Your Group 🎉", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")],
                    [InlineKeyboardButton("⌂ Support ⌂", url=SUPPORT_GROUP)]
                ])
                
                warn_msg = await message.reply_text(text, reply_markup=buttons)
                
                # Auto-Delete Warning
                await asyncio.sleep(60)
                try: await warn_msg.delete()
                except: pass

        except Exception as e:
            # Download fail or other error
            pass
        
