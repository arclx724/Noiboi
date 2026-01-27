import os
import aiohttp
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus
from config import BOT_USERNAME, SUPPORT_GROUP, OWNER_ID
import db

# SightEngine URL
API_URL = "https://api.sightengine.com/1.0/check.json"
TEMP_DOWNLOAD_PATH = "downloads/" 

# Create download folder if it doesn't exist to prevent errors
if not os.path.exists(TEMP_DOWNLOAD_PATH):
    os.makedirs(TEMP_DOWNLOAD_PATH)

def register_antinsfw_handlers(app: Client):

    # ======================================================
    # 1. API MANAGEMENT (Add/Check Keys)
    # ======================================================

    @app.on_message(filters.command(["addapi", "addamthy"]) & filters.private)
    async def add_nsfw_api_cmd(client, message):
        command_used = message.command[0]
        
        # Security: Only Owner can use /addapi
        if command_used == "addapi":
            if message.from_user.id != int(OWNER_ID):
                await message.reply_text("❌ **Access Denied!** Only the Owner can use this command.")
                return

        # Check for correct usage
        if len(message.command) != 3:
            await message.reply_text(f"Usage: `/{command_used} <api_user> <api_secret>`")
            return
        
        api_user = message.command[1]
        api_secret = message.command[2]
        
        try:
            # Add to Database
            await db.add_nsfw_api(api_user, api_secret)
            
            if command_used == "addamthy":
                await message.reply_text(f"🎉 **Thanks for contributing!**\nAPI Key Added successfully.")
            else:
                await message.reply_text(f"✅ **API Added Successfully!**")
        except Exception as e:
            await message.reply_text(f"Error: {e}")

    @app.on_message(filters.command("checkapi") & filters.private)
    async def check_api_stats(client, message):
        # Only Owner can check stats to protect privacy
        if message.from_user.id != int(OWNER_ID):
            return
        
        count = await db.get_all_nsfw_apis_count()
        
        # Calculation: 1 Free SightEngine Key = 2000 Scans/Month
        total_scans = count * 2000
        
        await message.reply_text(
            f"📊 **SightEngine Stats**\n\n"
            f"🔑 **Active Keys:** `{count}`\n"
            f"📉 **Est. Scans Left:** `~{total_scans}`\n\n"
            f"ℹ️ _The bot will automatically remove keys from the database when their limit is reached._"
        )

    # ======================================================
    # 2. GROUP SETTINGS (On/Off)
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
                await message.reply_text("🔞 **Anti-NSFW System Enabled!**\nNSFW photos, stickers, and videos will now be auto-deleted.")
            elif arg == "off":
                await db.set_antinsfw_status(message.chat.id, False)
                await message.reply_text("😌 **Anti-NSFW System Disabled!**")
        else:
            await message.reply_text("Usage: `/antinsfw on` or `/antinsfw off`")

    # ======================================================
    # 3. SCANNER LOGIC (Disk-Based & Robust Parsing)
    # ======================================================

    async def scan_file_on_disk(file_path):
        """
        Reads a file from the local disk and sends it to SightEngine API.
        Handles API rotation if a key is exhausted or invalid.
        """
        api_data = await db.get_nsfw_api()
        if not api_data:
            print("DEBUG: No API Keys available! Please add keys using /addapi")
            return None 

        try:
            data = aiohttp.FormData()
            # Request detection for Nudity, Weapons (WAD), and Gore
            data.add_field('models', 'nudity,wad,gore')
            data.add_field('api_user', api_data['api_user'])
            data.add_field('api_secret', api_data['api_secret'])
            
            # Open file in binary mode
            with open(file_path, 'rb') as f:
                data.add_field('media', f, filename='image.jpg')

                async with aiohttp.ClientSession() as session:
                    async with session.post(API_URL, data=data) as resp:
                        result = await resp.json()
            
            # Check for API Errors (Limit Exceeded or Invalid Key)
            if result['status'] == 'failure':
                error_code = result.get('error', {}).get('code')
                # Code 21 = Rate Limit, 23 = Monthly Limit, 103 = Invalid Key
                if error_code in [21, 23, 103]: 
                    print(f"DEBUG: Removing exhausted/invalid API ({api_data['api_user']})...")
                    await db.remove_nsfw_api(api_data['api_user'])
                    # Retry recursively with the next available key
                    return await scan_file_on_disk(file_path)
                return None
            
            return result

        except Exception as e:
            print(f"DEBUG: Scan Error: {e}")
            return None

    @app.on_message(filters.group & (filters.photo | filters.video | filters.sticker | filters.document | filters.animation), group=35)
    async def nsfw_watcher(client, message):
        chat_id = message.chat.id
        
        # 1. Check if Anti-NSFW is enabled in this group
        if not await db.is_antinsfw_enabled(chat_id):
            return

        # 2. Identify the Media Type and get the correct file object
        media = None
        
        if message.photo:
            media = message.photo
        elif message.sticker:
            if message.sticker.thumbs:
                # Scan the largest available thumbnail for stickers
                media = message.sticker.thumbs[-1]
            elif not message.sticker.is_animated and not message.sticker.is_video:
                # If it's a static sticker (webp), scan the file itself
                media = message.sticker
        elif message.video:
            if message.video.thumbs:
                # Scan the largest thumbnail of the video
                media = message.video.thumbs[-1]
        elif message.animation: 
            if message.animation.thumbs:
                # Scan the thumbnail of the GIF
                media = message.animation.thumbs[-1]
        elif message.document and "image" in message.document.mime_type:
            media = message.document

        if not media:
            return 

        # Create a unique filename to avoid conflicts between concurrent scans
        file_path = os.path.join(TEMP_DOWNLOAD_PATH, f"scan_{chat_id}_{message.id}.jpg")

        try:
            # 3. Size Limit Check (5MB) to save bandwidth and speed up processing
            if media.file_size > 5 * 1024 * 1024: 
                return 

            # 4. Download media to Disk
            await client.download_media(media, file_name=file_path)
            
            # Verify file exists
            if not os.path.exists(file_path): 
                return

            # 5. Send to SightEngine for Scanning
            result = await scan_file_on_disk(file_path)
            
            # 6. Cleanup: Delete the file immediately after scanning
            try: os.remove(file_path)
            except: pass

            if not result: 
                return 

            # 7. Parse Score (Robust Logic for Dict vs Float)
            nsfw_score = 0
            
            # --- Nudity Check ---
            if 'nudity' in result:
                # 'nudity' is usually a dict: {'raw': 0.1, 'safe': 0.9, 'partial': 0.0}
                raw = result['nudity'].get('raw', 0)
                partial = result['nudity'].get('partial', 0)
                nsfw_score = max(nsfw_score, raw, partial)
            
            # --- Weapon / Drugs Check ---
            if 'wad' in result:
                # 'wad' is a dict: {'weapon': 0.9, 'drugs': 0.0 ...}
                weapon = result['wad'].get('weapon', 0)
                nsfw_score = max(nsfw_score, weapon)
            elif 'weapon' in result:
                # Handle inconsistent API responses where 'weapon' might be at root
                w = result['weapon']
                if isinstance(w, dict): 
                    nsfw_score = max(nsfw_score, w.get('prob', 0))
                elif isinstance(w, float) or isinstance(w, int): 
                    nsfw_score = max(nsfw_score, w)

            # --- Gore Check ---
            if 'gore' in result:
                g = result['gore']
                # Gore can be {'prob': 0.9} OR just 0.9 directly. Handle both.
                if isinstance(g, dict): 
                    gore_prob = g.get('prob', 0)
                    nsfw_score = max(nsfw_score, gore_prob)
                elif isinstance(g, float) or isinstance(g, int):
                    nsfw_score = max(nsfw_score, g)

            # 8. ACTION: Delete if Score > 0.60 (60%)
            if nsfw_score > 0.60:
                percent = int(nsfw_score * 100)
                
                # Delete the message
                try: await message.delete()
                except: pass # Bot might not have delete rights
                
                # Send Warning Message
                text = (
                    f"⚠️ **NSFW Detected!**\n"
                    f"Hey {message.from_user.mention}, NSFW content is not allowed here!\n"
                    f"**Detection:** {percent}% (Nudity/Violence)\n"
                    f"Action: **Deleted** 🗑️"
                )
                
                buttons = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Add Me To Your Group 🎉", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")],
                    [InlineKeyboardButton("Support", url=SUPPORT_GROUP)]
                ])
                
                warn_msg = await message.reply_text(text, reply_markup=buttons)
                
                # Auto-delete warning after 60 seconds
                await asyncio.sleep(60)
                try: await warn_msg.delete()
                except: pass

        except Exception as e:
            print(f"DEBUG CRITICAL ERROR: {e}")
            # Ensure file is deleted even if a critical error occurs
            if os.path.exists(file_path):
                try: os.remove(file_path)
                except: pass

            
