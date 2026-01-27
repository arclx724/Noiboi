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

    @app.on_message(filters.command(["addapi", "addamthy"]) & filters.private)
    async def add_nsfw_api_cmd(client, message):
        print("DEBUG: Command received!") 
        
        command_used = message.command[0]
        
        if command_used == "addapi":
            if message.from_user.id != int(OWNER_ID):
                await message.reply_text("❌ Access Denied!")
                return

        if len(message.command) != 3:
            await message.reply_text(f"Usage: `/{command_used} <api_user> <api_secret>`")
            return
        
        api_user = message.command[1]
        api_secret = message.command[2]
        
        print(f"DEBUG: Trying to save {api_user}...") 

        try:
            await db.add_nsfw_api(api_user, api_secret)
            print("DEBUG: Saved successfully!") 
        except Exception as e:
            print(f"DEBUG ERROR: {e}") 
            await message.reply_text(f"Error: {e}")
            return

        await message.reply_text(f"✅ **API Added!**")

    @app.on_message(filters.command("checkapi") & filters.private)
    async def check_api_stats(client, message):
        if message.from_user.id != int(OWNER_ID):
            return
        count = await db.get_all_nsfw_apis_count()
        await message.reply_text(f"📊 **Total APIs:** `{count}`")

    # ======================================================
    # 2. GROUP COMMANDS
    # ======================================================

    @app.on_message(filters.command("antinsfw") & filters.group)
    async def antinsfw_switch(client, message):
        user = await client.get_chat_member(message.chat.id, message.from_user.id)
        if user.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            await message.reply_text("❌ Access Denied!")
            return

        if len(message.command) > 1:
            arg = message.command[1].lower()
            if arg == "on":
                await db.set_antinsfw_status(message.chat.id, True)
                await message.reply_text("🔞 **Anti-NSFW Enabled!**")
            elif arg == "off":
                await db.set_antinsfw_status(message.chat.id, False)
                await message.reply_text("😌 **Anti-NSFW Disabled!**")

    # ======================================================
    # 3. SCANNER LOGIC (FIXED)
    # ======================================================

    async def scan_image(image_bytes):
        api_data = await db.get_nsfw_api()
        if not api_data:
            print("DEBUG: No API Keys found in DB!")
            return None 

        data = aiohttp.FormData()
        data.add_field('models', 'nudity,wad,gore')
        data.add_field('api_user', api_data['api_user'])
        data.add_field('api_secret', api_data['api_secret'])
        data.add_field('media', image_bytes, filename='image.jpg')

        try:
            print(f"DEBUG: Sending to SightEngine using user: {api_data['api_user']}...")
            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL, data=data) as resp:
                    result = await resp.json()
            
            print(f"DEBUG: API Raw Result: {result}") 

            if result['status'] == 'failure':
                error_code = result.get('error', {}).get('code')
                print(f"DEBUG: API Failure Code: {error_code}")
                if error_code in [21, 23, 103]: 
                    print("DEBUG: Removing bad API key...")
                    await db.remove_nsfw_api(api_data['api_user'])
                    return await scan_image(image_bytes) 
                return None
            
            return result
        except Exception as e:
            print(f"DEBUG: Request Error: {e}")
            return None

    @app.on_message(filters.group & (filters.photo | filters.video | filters.sticker | filters.document | filters.animation), group=35)
    async def nsfw_watcher(client, message):
        chat_id = message.chat.id
        
        # Check enabled
        if not await db.is_antinsfw_enabled(chat_id):
            return

        print(f"\n--- NEW MEDIA DETECTED in Chat {chat_id} ---")

        # 1. Extract Media
        media = None
        
        if message.photo:
            media = message.photo
            print("DEBUG: Media is PHOTO")
        elif message.sticker:
            print(f"DEBUG: Media is STICKER (Animated: {message.sticker.is_animated}, Video: {message.sticker.is_video})")
            if message.sticker.thumbs:
                # FIX: Use [-1] for largest thumbnail
                media = message.sticker.thumbs[-1] 
                print("DEBUG: Sticker Thumbnail Found (Scanning thumb)")
            elif not message.sticker.is_animated and not message.sticker.is_video:
                media = message.sticker
                print("DEBUG: Static Sticker (Scanning direct file)")
            else:
                print("DEBUG: Sticker has NO thumbs and is Animated. Skipping.")
        elif message.video:
            if message.video.thumbs:
                media = message.video.thumbs[-1]
                print("DEBUG: Video Thumbnail Found")
        elif message.animation: 
            if message.animation.thumbs:
                media = message.animation.thumbs[-1]
                print("DEBUG: GIF Thumbnail Found")

        if not media:
            print("DEBUG: No scannable media found. Exiting.")
            return 

        # 2. Download
        try:
            if media.file_size > 2 * 1024 * 1024: 
                print("DEBUG: File too big (>2MB). Skipping.")
                return 

            print("DEBUG: Downloading media...")
            file_stream = io.BytesIO()
            
            # --- FIX APPLIED HERE ---
            # Humne 'file_ref' hata diya aur direct 'media' object pass kiya
            await client.download_media(media, file_name=file_stream)
            
            file_stream.seek(0)
            print("DEBUG: Download complete. Scanning...")
            
            # 3. Scan
            result = await scan_image(file_stream)
            
            if not result:
                print("DEBUG: Scan returned None (API Error or Empty).")
                return 

            # 4. Check Score
            nsfw_score = 0
            if 'nudity' in result:
                raw = result['nudity'].get('raw', 0)
                partial = result['nudity'].get('partial', 0)
                nsfw_score = max(raw, partial)
            
            if 'weapon' in result and result['weapon'] > 0.8:
                nsfw_score = max(nsfw_score, result['weapon'])
            if 'gore' in result and result['gore'] > 0.8:
                nsfw_score = max(nsfw_score, result['gore'])

            print(f"DEBUG: FINAL NSFW SCORE: {nsfw_score}")

            # 5. ACTION
            if nsfw_score > 0.60:
                print("DEBUG: NSFW DETECTED! DELETING...")
                percent = int(nsfw_score * 100)
                
                try: await message.delete()
                except: print("DEBUG: Delete Failed (No Rights?)")
                
                text = (
                    f"⚠️ **NSFW Detected!** ({percent}%)\n"
                    f"Action: **Deleted** 🗑️"
                )
                
                buttons = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Add Me 🎉", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")],
                    [InlineKeyboardButton("Support", url=SUPPORT_GROUP)]
                ])
                
                warn_msg = await message.reply_text(text, reply_markup=buttons)
                
                await asyncio.sleep(60)
                try: await warn_msg.delete()
                except: pass
            else:
                print("DEBUG: Content is Safe.")

        except Exception as e:
            print(f"DEBUG CRITICAL ERROR: {e}")
            
