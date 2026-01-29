import os
import io  # Memory stream ke liye zaroori
import aiohttp
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus
from config import BOT_USERNAME, SUPPORT_GROUP, OWNER_ID
import db

# SightEngine URL
API_URL = "https://api.sightengine.com/1.0/check.json"

def register_antinsfw_handlers(app: Client):

    # ======================================================
    # 1. API MANAGEMENT (Add/Check Keys)
    # ======================================================

    @app.on_message(filters.command(["addapi", "addamthy"]) & filters.private)
    async def add_nsfw_api_cmd(client, message):
        if len(message.command) != 3:
            await message.reply_text("Usage: `/addapi <api_user> <api_secret>`")
            return
        
        # Security Check: Only Owner
        if message.command[0] == "addapi" and message.from_user.id != int(OWNER_ID):
            await message.reply_text("❌ **Access Denied!** Only Owner can use this.")
            return

        api_user = message.command[1]
        api_secret = message.command[2]
        
        try:
            await db.add_nsfw_api(api_user, api_secret)
            if message.command[0] == "addamthy":
                await message.reply_text(f"🎉 **Thanks for contributing!**\nAPI Key Added successfully.")
            else:
                await message.reply_text("✅ **API Added Successfully!**")
        except Exception as e:
            await message.reply_text(f"Error: {e}")

    @app.on_message(filters.command("checkapi") & filters.private)
    async def check_api_stats(client, message):
        if message.from_user.id != int(OWNER_ID):
            return
        
        count = await db.get_all_nsfw_apis_count()
        # 1 Key = 2000 requests approx
        total_scans = count * 2000
        
        await message.reply_text(
            f"📊 **SightEngine Stats**\n\n"
            f"🔑 **Active Keys:** `{count}`\n"
            f"📉 **Est. Capacity:** `~{total_scans} Scans`"
        )

    # ======================================================
    # 2. GROUP SETTINGS (Enable/Disable)
    # ======================================================

    @app.on_message(filters.command("antinsfw") & filters.group)
    async def antinsfw_switch(client, message):
        # Admin Permission Check
        user = await client.get_chat_member(message.chat.id, message.from_user.id)
        if user.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            await message.reply_text("❌ **Access Denied!** Only Admins can use this command.")
            return

        if len(message.command) > 1:
            arg = message.command[1].lower()
            if arg == "on":
                await db.set_antinsfw_status(message.chat.id, True)
                await message.reply_text("🔞 **Anti-NSFW System Enabled!**\nScanning incoming media...")
            elif arg == "off":
                await db.set_antinsfw_status(message.chat.id, False)
                await message.reply_text("😌 **Anti-NSFW System Disabled!**")
        else:
            await message.reply_text("Usage: `/antinsfw on` or `/antinsfw off`")

    # ======================================================
    # 3. SCANNER LOGIC (Optimized for Speed)
    # ======================================================

    async def scan_file_in_memory(file_stream):
        """
        Uploads file from RAM to API. Handles key rotation if limit reached.
        """
        api_data = await db.get_nsfw_api()
        if not api_data:
            return None 

        try:
            data = aiohttp.FormData()
            data.add_field('models', 'nudity,wad,gore')
            data.add_field('api_user', api_data['api_user'])
            data.add_field('api_secret', api_data['api_secret'])
            
            # Pointer start pe le jao taaki file read ho sake
            file_stream.seek(0)
            data.add_field('media', file_stream, filename='image.jpg')

            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL, data=data) as resp:
                    result = await resp.json()
            
            # API Error Handling (Rate Limits)
            if result['status'] == 'failure':
                error_code = result.get('error', {}).get('code')
                # 21: Rate limit, 23: Monthly limit, 103: Invalid Key
                if error_code in [21, 23, 103]: 
                    await db.remove_nsfw_api(api_data['api_user'])
                    return await scan_file_in_memory(file_stream) # Retry with next key
                return None
            
            return result
        except Exception as e:
            # print(f"DEBUG: Scan Error: {e}")
            return None

    @app.on_message(filters.group & (filters.photo | filters.video | filters.sticker | filters.document | filters.animation), group=35)
    async def nsfw_watcher(client, message):
        chat_id = message.chat.id
        
        # Check Database Status
        if not await db.is_antinsfw_enabled(chat_id):
            return

        media = None
        
        # --- FAST SELECTION LOGIC (Thumbnail Priority) ---
        if message.photo:
            # Original photo ke bajaye chhota thumbnail lo (Speed up 10x)
            if message.photo.thumbs:
                media = message.photo.thumbs[-1]
            else:
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
            if message.document.thumbs:
                media = message.document.thumbs[-1]
            else:
                media = message.document
        # ------------------------------------------------

        if not media:
            return 

        # Size Check (Skip if > 5MB, though thumbs are small)
        if hasattr(media, 'file_size') and media.file_size > 5 * 1024 * 1024: 
            return 

        try:
            # 1. Download to RAM (No Disk I/O)
            file_stream = await client.download_media(media, in_memory=True)
            
            if not file_stream:
                return

            # 2. Scan via API
            result = await scan_file_in_memory(file_stream)
            
            if not result: 
                return 

            # 3. Parse NSFW Score
            nsfw_score = 0
            
            # Nudity
            if 'nudity' in result:
                nsfw_score = max(nsfw_score, result['nudity'].get('raw', 0), result['nudity'].get('partial', 0))
            
            # Weapon / Drugs
            if 'wad' in result:
                nsfw_score = max(nsfw_score, result['wad'].get('weapon', 0))
            elif 'weapon' in result:
                w = result['weapon']
                val = w.get('prob', 0) if isinstance(w, dict) else w if isinstance(w, (float, int)) else 0
                nsfw_score = max(nsfw_score, val)

            # Gore
            if 'gore' in result:
                g = result['gore']
                val = g.get('prob', 0) if isinstance(g, dict) else g if isinstance(g, (float, int)) else 0
                nsfw_score = max(nsfw_score, val)

            # 4. ACTION (Threshold > 60%)
            if nsfw_score > 0.60:
                percent = int(nsfw_score * 100)
                
                # Step A: Delete First (User experience: Instant removal)
                try: await message.delete()
                except: pass 
                
                # Step B: Prepare Alert
                text = (
                    f"⚠️ **NSFW Detected!**\n"
                    f"User: {message.from_user.mention}\n"
                    f"Certainty: {percent}%\n"
                    f"**Action: Deleted** 🗑️"
                )
                
                buttons = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Add Me 🛡️", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")]
                ])
                
                # Step C: Send Alert Asynchronously (Don't wait for it)
                asyncio.create_task(send_alert(message, text, buttons))

        except Exception as e:
            # Production mein errors print na karein taaki logs na bharein
            pass

    # Helper function for Non-Blocking Alert
    async def send_alert(message, text, buttons):
        try:
            warn_msg = await message.reply_text(text, reply_markup=buttons)
            await asyncio.sleep(60) # 60 sec baad warning bhi delete
            await warn_msg.delete()
        except:
            pass
            
