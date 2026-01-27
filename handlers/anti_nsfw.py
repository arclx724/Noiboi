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
TEMP_DOWNLOAD_PATH = "downloads/" # Yahan files temporarily save hongi

# Folder bana lete hain agar nahi hai to
if not os.path.exists(TEMP_DOWNLOAD_PATH):
    os.makedirs(TEMP_DOWNLOAD_PATH)

def register_antinsfw_handlers(app: Client):

    # ======================================================
    # 1. API MANAGEMENT (Add/Check Keys)
    # ======================================================

    @app.on_message(filters.command(["addapi", "addamthy"]) & filters.private)
    async def add_nsfw_api_cmd(client, message):
        command_used = message.command[0]
        
        # Owner Check for /addapi
        if command_used == "addapi":
            if message.from_user.id != int(OWNER_ID):
                await message.reply_text("❌ Access Denied! Sirf Owner use kar sakta hai.")
                return

        if len(message.command) != 3:
            await message.reply_text(f"Usage: `/{command_used} <api_user> <api_secret>`")
            return
        
        api_user = message.command[1]
        api_secret = message.command[2]
        
        try:
            await db.add_nsfw_api(api_user, api_secret)
            if command_used == "addamthy":
                await message.reply_text(f"🎉 **Thanks for helping!**\nAPI Key Added.")
            else:
                await message.reply_text(f"✅ **API Added Successfully!**")
        except Exception as e:
            await message.reply_text(f"Error: {e}")

    @app.on_message(filters.command("checkapi") & filters.private)
    async def check_api_stats(client, message):
        if message.from_user.id != int(OWNER_ID):
            return
        count = await db.get_all_nsfw_apis_count()
        await message.reply_text(f"📊 **Total Active APIs:** `{count}`")

    # ======================================================
    # 2. GROUP SETTINGS (On/Off)
    # ======================================================

    @app.on_message(filters.command("antinsfw") & filters.group)
    async def antinsfw_switch(client, message):
        user = await client.get_chat_member(message.chat.id, message.from_user.id)
        if user.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            await message.reply_text("❌ Sirf Admins ye command use kar sakte hain!")
            return

        if len(message.command) > 1:
            arg = message.command[1].lower()
            if arg == "on":
                await db.set_antinsfw_status(message.chat.id, True)
                await message.reply_text("🔞 **Anti-NSFW System Enabled!**\nAb gandi photos aur stickers delete ho jayenge.")
            elif arg == "off":
                await db.set_antinsfw_status(message.chat.id, False)
                await message.reply_text("😌 **Anti-NSFW System Disabled!**")
        else:
            await message.reply_text("Usage: `/antinsfw on` or `/antinsfw off`")

    # ======================================================
    # 3. SCANNER LOGIC (Disk-Based: Stable)
    # ======================================================

    async def scan_file_on_disk(file_path):
        """File ko disk se padh kar scan karega"""
        api_data = await db.get_nsfw_api()
        if not api_data:
            print("DEBUG: No API Keys available!")
            return None 

        try:
            data = aiohttp.FormData()
            data.add_field('models', 'nudity,wad,gore')
            data.add_field('api_user', api_data['api_user'])
            data.add_field('api_secret', api_data['api_secret'])
            
            # File open karke bhejo
            with open(file_path, 'rb') as f:
                data.add_field('media', f, filename='image.jpg')

                async with aiohttp.ClientSession() as session:
                    async with session.post(API_URL, data=data) as resp:
                        result = await resp.json()
            
            # API Error Handling (Limit/Invalid)
            if result['status'] == 'failure':
                error_code = result.get('error', {}).get('code')
                if error_code in [21, 23, 103]: 
                    print(f"DEBUG: Bad API found ({api_data['api_user']}), removing...")
                    await db.remove_nsfw_api(api_data['api_user'])
                    return await scan_file_on_disk(file_path) # Retry with next key
                return None
            
            return result

        except Exception as e:
            print(f"DEBUG: Scan Error: {e}")
            return None

    @app.on_message(filters.group & (filters.photo | filters.video | filters.sticker | filters.document | filters.animation), group=35)
    async def nsfw_watcher(client, message):
        chat_id = message.chat.id
        
        # Check enabled
        if not await db.is_antinsfw_enabled(chat_id):
            return

        # 1. Decide Media to Scan
        media = None
        is_video_sticker = False
        
        if message.photo:
            media = message.photo
        elif message.sticker:
            if message.sticker.thumbs:
                media = message.sticker.thumbs[-1] # Largest thumb
                is_video_sticker = True
            elif not message.sticker.is_animated and not message.sticker.is_video:
                media = message.sticker
        elif message.video:
            if message.video.thumbs:
                media = message.video.thumbs[-1]
                is_video_sticker = True
        elif message.animation: 
            if message.animation.thumbs:
                media = message.animation.thumbs[-1]
                is_video_sticker = True
        elif message.document and "image" in message.document.mime_type:
            media = message.document

        if not media:
            return 

        # 2. Setup File Path
        # Unique name banayenge taaki mix na ho
        file_path = os.path.join(TEMP_DOWNLOAD_PATH, f"scan_{chat_id}_{message.id}.jpg")

        try:
            # 2MB Limit check (Stickers/Thumbs usually small hote hain)
            if media.file_size > 2 * 1024 * 1024: 
                return 

            # 3. Download to Disk (Yeh fail nahi hota)
            await client.download_media(media, file_name=file_path)
            
            if not os.path.exists(file_path):
                print("DEBUG: File download failed.")
                return

            # 4. Scan
            result = await scan_file_on_disk(file_path)
            
            # 5. Cleanup (File delete karna zaroori hai)
            try:
                os.remove(file_path)
            except: pass

            if not result:
                return 

            # 6. Check Scores
            nsfw_score = 0
            if 'nudity' in result:
                raw = result['nudity'].get('raw', 0)
                partial = result['nudity'].get('partial', 0)
                nsfw_score = max(raw, partial)
            
            if 'weapon' in result and result['weapon'] > 0.8:
                nsfw_score = max(nsfw_score, result['weapon'])
            if 'gore' in result and result['gore'] > 0.8:
                nsfw_score = max(nsfw_score, result['gore'])

            # 7. Action: Delete if NSFW > 60%
            if nsfw_score > 0.60:
                percent = int(nsfw_score * 100)
                
                try: await message.delete()
                except: pass 
                
                text = (
                    f"⚠️ **NSFW Detected!**\n"
                    f"Hey {message.from_user.mention}, ye content allowed nahi hai!\n"
                    f"**Detection:** {percent}% Nudity/Gore\n"
                    f"Action: **Deleted** 🗑️"
                )
                
                buttons = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Add Me 🎉", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")],
                    [InlineKeyboardButton("Support", url=SUPPORT_GROUP)]
                ])
                
                warn_msg = await message.reply_text(text, reply_markup=buttons)
                
                # Auto-delete warning
                await asyncio.sleep(60)
                try: await warn_msg.delete()
                except: pass

        except Exception as e:
            print(f"DEBUG CRITICAL: {e}")
            # Error aane par bhi file delete honi chahiye
            if os.path.exists(file_path):
                try: os.remove(file_path)
                except: pass
                    
