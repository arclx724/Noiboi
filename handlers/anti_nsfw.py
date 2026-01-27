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
    # 1. API MANAGEMENT (Add Keys)
    # ======================================================

    # Combined Handler for /addapi (Owner) and /addamthy (Public)
    @app.on_message(filters.command(["addapi", "addamthy"]) & filters.private)
    async def add_nsfw_api_cmd(client, message):
        print("DEBUG: Command received!") # <--- DEBUG LINE 1
        
        command_used = message.command[0] # Check konsa command use hua
        
        # LOGIC: Agar /addapi hai, toh Owner check karo
        if command_used == "addapi":
            if message.from_user.id != int(OWNER_ID):
                await message.reply_text("❌ **Access Denied!**\n`/addapi` is reserved for the Owner.\nYou can use `/addamthy` to contribute keys.")
                return

        # LOGIC: Agar /addamthy hai, toh koi check nahi (Sabke liye open)

        # Format Check: /command <user> <secret>
        if len(message.command) != 3:
            await message.reply_text(f"Usage: `/{command_used} <api_user> <api_secret>`")
            return
        
        api_user = message.command[1]
        api_secret = message.command[2]
        
        print(f"DEBUG: Trying to save {api_user}...") # <--- DEBUG LINE 2

        try:
            # Database mein add karo
            await db.add_nsfw_api(api_user, api_secret)
            print("DEBUG: Saved successfully!") # <--- DEBUG LINE 3
        except Exception as e:
            print(f"DEBUG ERROR: {e}") # <--- ERROR CATCHING
            await message.reply_text(f"⚠️ **Database Error:** {e}")
            return
        
        # Success Message
        if command_used == "addamthy":
            await message.reply_text(f"🎉 **Thanks for contributing!**\nAPI Key Added successfully.\nUser: `{api_user}`")
        else:
            await message.reply_text(f"✅ **API Added!**\nUser: `{api_user}`")

    # Check Stats (Sirf Owner dekh sakta hai ki kitni keys bachi hain)
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
    # 3. SCANNER LOGIC (Core System)
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
            return 

        # 3. Download to RAM
        try:
            # 2MB check
            if media.file_size > 2 * 1024 * 1024: 
                return 

            file_stream = io.BytesIO()
            await client.download_media(media.file_id, file_ref=media.file_ref, file_name=file_stream)
            file_stream.seek(0)
            
            # 4. Scan
            result = await scan_image(file_stream)
            
            if not result:
                return 

            # 5. Check Score (Threshold > 60%)
            nsfw_score = 0
            
            if 'nudity' in result:
                raw = result['nudity'].get('raw', 0)
                partial = result['nudity'].get('partial', 0)
                nsfw_score = max(raw, partial)
            
            if 'weapon' in result and result['weapon'] > 0.8:
                nsfw_score = max(nsfw_score, result['weapon'])
            if 'gore' in result and result['gore'] > 0.8:
                nsfw_score = max(nsfw_score, result['gore'])

            # 6. ACTION
            if nsfw_score > 0.60:
                percent = int(nsfw_score * 100)
                
                try: await message.delete()
                except: pass 
                
                text = (
                    f"⚠️ **NSFW Content Detected!**\n"
                    f"Hey {message.from_user.mention}, your message contained {percent}% NSFW content.\n"
                    f"Action: **Deleted** 🗑️\n\n"
                    f"⏳ **This warning auto-deletes in 60s.**"
                )
                
                buttons = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Add Me To Your Group 🎉", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")],
                    [InlineKeyboardButton("⌂ Support ⌂", url=SUPPORT_GROUP)]
                ])
                
                warn_msg = await message.reply_text(text, reply_markup=buttons)
                
                await asyncio.sleep(60)
                try: await warn_msg.delete()
                except: pass

        except Exception:
            pass
            
