import os
import io # New Import for Memory Stream
import aiohttp
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus
from config import BOT_USERNAME, SUPPORT_GROUP, OWNER_ID
import db

# SightEngine URL
API_URL = "https://api.sightengine.com/1.0/check.json"

# Note: TEMP_DOWNLOAD_PATH ki ab zarurat nahi hai kyunki hum RAM use karenge

def register_antinsfw_handlers(app: Client):

    # ... (API MANAGEMENT aur GROUP SETTINGS wala code same rahega) ...
    # Sirf SCANNER LOGIC change ho raha hai niche:

    # ======================================================
    # 3. SCANNER LOGIC (RAM-Based & Faster)
    # ======================================================

    async def scan_file_in_memory(file_stream):
        """
        Receives a BytesIO object (file in RAM) and sends it directly to API.
        No disk read/write makes this much faster.
        """
        api_data = await db.get_nsfw_api()
        if not api_data:
            return None 

        try:
            data = aiohttp.FormData()
            data.add_field('models', 'nudity,wad,gore')
            data.add_field('api_user', api_data['api_user'])
            data.add_field('api_secret', api_data['api_secret'])
            
            # Important: Reset pointer to start of file
            file_stream.seek(0)
            
            # Send the BytesIO object directly with a filename
            data.add_field('media', file_stream, filename='image.jpg')

            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL, data=data) as resp:
                    result = await resp.json()
            
            # Check for API Errors (Limit Exceeded)
            if result['status'] == 'failure':
                error_code = result.get('error', {}).get('code')
                if error_code in [21, 23, 103]: 
                    await db.remove_nsfw_api(api_data['api_user'])
                    return await scan_file_in_memory(file_stream) # Retry with next key
                return None
            
            return result

        except Exception as e:
            print(f"DEBUG: Scan Error: {e}")
            return None

    @app.on_message(filters.group & (filters.photo | filters.video | filters.sticker | filters.document | filters.animation), group=35)
    async def nsfw_watcher(client, message):
        chat_id = message.chat.id
        
        if not await db.is_antinsfw_enabled(chat_id):
            return

        media = None
        # Logic to select media remains same
        if message.photo:
            media = message.photo
        elif message.sticker:
            if message.sticker.thumbs:
                media = message.sticker.thumbs[-1]
            elif not message.sticker.is_animated and not message.sticker.is_video:
                media = message.sticker
        elif message.video:
            if message.video.thumbs:
                media = message.video.thumbs[-1]
        elif message.animation: 
            if message.animation.thumbs:
                media = message.animation.thumbs[-1]
        elif message.document and "image" in message.document.mime_type:
            media = message.document

        if not media:
            return 

        try:
            # OPTIMIZATION 1: Size Limit strict check
            if media.file_size > 5 * 1024 * 1024: 
                return 

            # OPTIMIZATION 2: Download to Memory (RAM) instead of Disk
            # This is significantly faster than download_media() with file path
            file_stream = await client.download_media(media, in_memory=True)
            
            if not file_stream:
                return

            # Send RAM stream to SightEngine
            result = await scan_file_in_memory(file_stream)
            
            # RAM automatically clears, no need to os.remove()

            if not result: 
                return 

            # --- Scoring Logic (Same as before) ---
            nsfw_score = 0
            
            if 'nudity' in result:
                raw = result['nudity'].get('raw', 0)
                partial = result['nudity'].get('partial', 0)
                nsfw_score = max(nsfw_score, raw, partial)
            
            if 'wad' in result:
                weapon = result['wad'].get('weapon', 0)
                nsfw_score = max(nsfw_score, weapon)
            elif 'weapon' in result:
                w = result['weapon']
                if isinstance(w, dict): nsfw_score = max(nsfw_score, w.get('prob', 0))
                elif isinstance(w, (float, int)): nsfw_score = max(nsfw_score, w)

            if 'gore' in result:
                g = result['gore']
                if isinstance(g, dict): nsfw_score = max(nsfw_score, g.get('prob', 0))
                elif isinstance(g, (float, int)): nsfw_score = max(nsfw_score, g)

            # --- Action ---
            if nsfw_score > 0.60:
                percent = int(nsfw_score * 100)
                
                try: await message.delete()
                except: pass 
                
                text = (
                    f"⚠️ **NSFW Detected!**\n"
                    f"Hey {message.from_user.mention}, NSFW content is not allowed!\n"
                    f"**Detection:** {percent}%\n"
                    f"Action: **Deleted** 🗑️"
                )
                
                buttons = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Add Me 🛡️", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")]
                ])
                
                # OPTIMIZATION 3: Send alert without waiting (create_task)
                # This ensures the bot doesn't hang waiting for the reply to send
                asyncio.create_task(send_alert(message, text, buttons))

        except Exception as e:
            print(f"DEBUG ERROR: {e}")

    # Helper function to handle alerting asynchronously
    async def send_alert(message, text, buttons):
        try:
            warn_msg = await message.reply_text(text, reply_markup=buttons)
            await asyncio.sleep(60)
            await warn_msg.delete()
        except:
            pass
            
