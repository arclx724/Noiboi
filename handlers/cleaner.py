import time
from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus, MessageEntityType
import db

# Anti-Flood Cache (RAM)
# Format: { (chat_id, user_id): [timestamp1, timestamp2, ...] }
FLOOD_CACHE = {}
FLOOD_LIMIT = 3
FLOOD_SECONDS = 20

def register_cleaner_handlers(app: Client):

    # ======================================================
    # 1. COMMANDS TO ENABLE/DISABLE FILTERS
    # ======================================================

    async def toggle_setting(message, command, db_setter, name):
        """Helper function to toggle settings"""
        chat_id = message.chat.id
        user_id = message.from_user.id

        # Admin Check
        member = await message.chat.get_member(user_id)
        if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            await message.reply_text("❌ **Access Denied!**\nOnly Admins Can Use This Command.")
            return

        if len(message.command) > 1:
            arg = message.command[1].lower()
            
            # Bot Permission Check
            bot_member = await message.chat.get_member(message._client.me.id)
            if not bot_member.privileges or not bot_member.privileges.can_delete_messages:
                await message.reply_text("⚠️ **Error:** I Don't Have **Delete Messages** Permission!")
                return

            if arg == "on":
                await db_setter(chat_id, True)
                await message.reply_text(f"✅ **{name} Enabled!**")
            elif arg == "off":
                await db_setter(chat_id, False)
                await message.reply_text(f"❌ **{name} Disabled!**")
            else:
                await message.reply_text(f"Usage: `/{command} on` or `/{command} off`")
        else:
            await message.reply_text(f"Usage: `/{command} on` or `/{command} off`")

    # Register Commands
    @app.on_message(filters.command("nocommands") & filters.group)
    async def cmd_nocommands(c, m): await toggle_setting(m, "nocommands", db.set_nocommands_status, "No-Commands")

    @app.on_message(filters.command("noevents") & filters.group)
    async def cmd_noevents(c, m): await toggle_setting(m, "noevents", db.set_noevents_status, "No-Events")

    @app.on_message(filters.command("nohashtags") & filters.group)
    async def cmd_nohashtags(c, m): await toggle_setting(m, "nohashtags", db.set_nohashtags_status, "No-Hashtags")

    @app.on_message(filters.command("antiflood") & filters.group)
    async def cmd_antiflood(c, m): await toggle_setting(m, "antiflood", db.set_antiflood_status, "Anti-Flood")

    @app.on_message(filters.command("nolinks") & filters.group)
    async def cmd_nolinks(c, m): await toggle_setting(m, "nolinks", db.set_nolinks_status, "No-Links")

    @app.on_message(filters.command("noforwards") & filters.group)
    async def cmd_noforwards(c, m): await toggle_setting(m, "noforwards", db.set_noforwards_status, "No-Forwards")

    @app.on_message(filters.command("nocontacts") & filters.group)
    async def cmd_nocontacts(c, m): await toggle_setting(m, "nocontacts", db.set_nocontacts_status, "No-Contacts")

    @app.on_message(filters.command("nolocations") & filters.group)
    async def cmd_nolocations(c, m): await toggle_setting(m, "nolocations", db.set_nolocations_status, "No-Locations")


    # ======================================================
    # 2. MASTER FILTER WATCHER (Checks Everything)
    # ======================================================
    
    @app.on_message(filters.group, group=30)
    async def master_cleaner(client, message):
        chat_id = message.chat.id
        
        # --- A. Service Messages (Join/Left) ---
        if message.service:
            if await db.is_noevents_enabled(chat_id):
                try: await message.delete()
                except: pass
            return

        # Ignore empty messages or edits (if not needed)
        if not message.from_user:
            return

        # --- B. Admin Bypass Check ---
        # Admins ke messages filter nahi honge (Except maybe commands if you want strict mode, but usually admins are safe)
        # Performance ke liye hum har message pe admin check kar rahe hain, ye zaroori hai.
        try:
            member = await message.chat.get_member(message.from_user.id)
            if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                return 
        except:
            pass

        # === 1. ANTI-FLOOD CHECK ===
        if await db.is_antiflood_enabled(chat_id):
            user_id = message.from_user.id
            now = time.time()
            key = (chat_id, user_id)
            
            # Get timestamps
            timestamps = FLOOD_CACHE.get(key, [])
            # Filter old timestamps (keep only last 20 seconds)
            timestamps = [t for t in timestamps if now - t < FLOOD_SECONDS]
            timestamps.append(now)
            FLOOD_CACHE[key] = timestamps
            
            if len(timestamps) > FLOOD_LIMIT:
                try: await message.delete()
                except: pass
                return # Delete kiya to aage check karne ki zarurat nahi

        # === 2. NO COMMANDS ===
        if message.text and message.text.startswith(("/", "!", ".")):
            if await db.is_nocommands_enabled(chat_id):
                try: await message.delete()
                except: pass
                return

        # === 3. NO FORWARDS ===
        if (message.forward_date or message.forward_from or message.forward_from_chat):
            if await db.is_noforwards_enabled(chat_id):
                try: await message.delete()
                except: pass
                return

        # === 4. NO LOCATIONS ===
        if message.location:
            if await db.is_nolocations_enabled(chat_id):
                try: await message.delete()
                except: pass
                return

        # === 5. NO CONTACTS ===
        if message.contact:
            if await db.is_nocontacts_enabled(chat_id):
                try: await message.delete()
                except: pass
                return

        # === 6. ENTITY CHECKS (Links, Hashtags, Mentions) ===
        # Check entities only if text/caption exists
        if message.entities or message.caption_entities:
            entities = message.entities or message.caption_entities
            has_link = False
            has_hashtag = False

            for entity in entities:
                # Check for Links/Mentions
                if entity.type in [MessageEntityType.URL, MessageEntityType.TEXT_LINK, MessageEntityType.MENTION]:
                    has_link = True
                # Check for Hashtags
                if entity.type == MessageEntityType.HASHTAG:
                    has_hashtag = True
            
            # --- ACTION: No Links ---
            if has_link or message.reply_markup: # reply_markup = buttons
                if await db.is_nolinks_enabled(chat_id):
                    try: await message.delete()
                    except: pass
                    return

            # --- ACTION: No Hashtags ---
            if has_hashtag:
                if await db.is_nohashtags_enabled(chat_id):
                    try: await message.delete()
                    except: pass
                    return
            
