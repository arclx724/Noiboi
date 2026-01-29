import os
import io  # Memory stream ke liye
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
        
        # Security Check
        if message.command[0] == "addapi" and message.from_user.id != int(OWNER_ID):
            await message.reply_text("❌ Only Owner can use this.")
            return

        api_user = message.command[1]
        api_secret = message.command[2]
        
        try:
            await db.add_nsfw_api(api_user, api_secret)
            await message.reply_text("✅ **API Added Successfully!**")
        except Exception as e:
            await message.reply_text(f"Error: {e}")

    @app.on_message(filters.command("checkapi") & filters.private)
    async def check_api_stats(client, message):
        if message.from_user.id != int(OWNER_ID):
            return
        count = await db.get_all_nsfw_apis_count()
        total_scans = count * 2000
        await message.reply_text(f"📊 **Stats:**\n🔑 Active Keys: `{count}`\n📉 Est. Scans: `~{total_scans}`")

    # ======================================================
    # 2. GROUP SETTINGS (Ye Missing Tha Aapke Code Mein)
    # ======================================================

    @app.on_message(filters.command("antinsfw") & filters.group)
    async def antinsfw_switch(client, message):
        # Admin Check
        user = await client.get_chat_member(message.chat.id, message.from_user.id)
        if user.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            await message.reply_text("❌ Only Admins can use this command.")
            return

        if len(message.command) > 1:
            arg = message.command[1].lower()
            if arg == "on":
                await db.set_antinsfw_status(message.chat.id, True)
                await message.reply_text("🔞 **Anti-NSFW Enabled!**\nScanning images & videos...")
            elif arg == "off":
                await db.set_antinsfw_status(message.chat.id, False)
                await message.reply_text("😌 **Anti-NSFW Disabled!**")
        else:
            await message.reply_text("Usage: `/antinsfw on` or `/antinsfw off`")

    # ======================================================
    # 3. SCANNER LOGIC (RAM-Based & Faster)
    # ======================================================

    async def scan_file_in_memory(file_stream):
        api_data = await db.get_nsfw_api()
        if not api_data: return None 

        try:
            data = aiohttp.FormData()
            data.add_field('models', 'nudity,wad,gore')
            data.add_field('api_user', api_data['api_user'])
            data.add_field('api_secret', api_data['api_secret'])
            
            file_stream.seek(0)
            data.add_field('media', file_stream, filename='image.jpg')

            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL, data=data) as resp:
                    result = await resp.json()
            
            if result['status'] == 'failure':
                error_code = result.get('error', {}).get('code')
                if error_code in [21, 23, 103]: 
                    await db.remove_nsfw_api(api_data['api_user'])
                    return await scan_file_in_memory(file_stream)
                return None
            return result
        except Exception as e:
            print(f"Scan Error: {e}")
            return None

    @app.on_message(filters.group & (filters.photo | filters.video | filters.sticker | filters.document | filters.animation), group=35)
    async def nsfw_watcher(client, message):
        chat_id = message.chat.id
        if not await db.is_antinsfw_enabled(chat_id): return

        media = None
        if message.photo: media = message.photo
        elif message.sticker:
            if message.sticker.thumbs: media = message.sticker.thumbs[-1]
            elif not message.sticker.is_animated and not message.sticker.is_video: media = message.sticker
        elif message.video:
            if message.video.thumbs: media = message.video.thumbs[-1]
        elif message.animation and message.animation.thumbs: media = message.animation.thumbs[-1]
        elif message.document and "image" in message.document.mime_type: media = message.document

        if not media or media.file_size > 5 * 1024 * 1024: return 

        try:
            file_stream = await client.download_media(media, in_memory=True)
            if not file_stream: return

            result = await scan_file_in_memory(file_stream)
            if not result: return 

            nsfw_score = 0
            if 'nudity' in result:
                nsfw_score = max(nsfw_score, result['nudity'].get('raw', 0), result['nudity'].get('partial', 0))
            if 'wad' in result:
                nsfw_score = max(nsfw_score, result['wad'].get('weapon', 0))
            elif 'weapon' in result:
                w = result['weapon']
                val = w.get('prob', 0) if isinstance(w, dict) else w if isinstance(w, (float, int)) else 0
                nsfw_score = max(nsfw_score, val)
            if 'gore' in result:
                g = result['gore']
                val = g.get('prob', 0) if isinstance(g, dict) else g if isinstance(g, (float, int)) else 0
                nsfw_score = max(nsfw_score, val)

            if nsfw_score > 0.60:
                try: await message.delete()
                except: pass 
                
                text = f"⚠️ **NSFW Detected!**\nUser: {message.from_user.mention}\nLevel: {int(nsfw_score*100)}%\n**Action: Deleted** 🗑️"
                buttons = InlineKeyboardMarkup([[InlineKeyboardButton("Add Me 🛡️", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")]])
                asyncio.create_task(send_alert(message, text, buttons))

        except Exception as e:
            print(f"Main Error: {e}")

    async def send_alert(message, text, buttons):
        try:
            m = await message.reply_text(text, reply_markup=buttons)
            await asyncio.sleep(60)
            await m.delete()
        except: pass
            
