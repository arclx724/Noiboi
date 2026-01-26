# ============================================================
# Group Manager Bot - Database Module
# ============================================================

import motor.motor_asyncio
from config import MONGO_URI, DB_NAME
import logging
import time

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s'
)

# Connect to MongoDB
try:
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    logging.info("✅ MongoDB connected successfully!")
except Exception as e:
    logging.error(f"❌ Failed to connect to MongoDB: {e}")

# ==========================================================
# 🟢 WELCOME MESSAGE SYSTEM
# ==========================================================

async def set_welcome_message(chat_id: int, text: str):
    await db.welcome.update_one(
        {"chat_id": chat_id},
        {"$set": {"message": text}},
        upsert=True
    )

async def get_welcome_message(chat_id: int):
    data = await db.welcome.find_one({"chat_id": chat_id})
    return data.get("message") if data else None

async def set_welcome_status(chat_id: int, status: bool):
    await db.welcome.update_one(
        {"chat_id": chat_id},
        {"$set": {"enabled": status}},
        upsert=True
    )

async def get_welcome_status(chat_id: int) -> bool:
    data = await db.welcome.find_one({"chat_id": chat_id})
    if not data:
        return True # Default is ON
    return data.get("enabled", True)

# ==========================================================
# 🔒 LOCK SYSTEM
# ==========================================================

async def set_lock(chat_id: int, lock_type: str, status: bool):
    await db.locks.update_one(
        {"chat_id": chat_id},
        {"$set": {f"locks.{lock_type}": status}},
        upsert=True
    )

async def get_locks(chat_id: int):
    data = await db.locks.find_one({"chat_id": chat_id})
    return data.get("locks", {}) if data else {}

# ==========================================================
# 🤬 ABUSE SYSTEM (Missing Functions Restored)
# ==========================================================

async def set_abuse_status(chat_id: int, status: bool):
    await db.abuse_settings.update_one(
        {"chat_id": chat_id},
        {"$set": {"enabled": status}},
        upsert=True
    )

async def is_abuse_enabled(chat_id: int) -> bool:
    data = await db.abuse_settings.find_one({"chat_id": chat_id})
    return data.get("enabled", False) if data else False

# ==========================================================
# ⚠️ WARN SYSTEM
# ==========================================================

async def add_warn(chat_id: int, user_id: int) -> int:
    data = await db.warns.find_one({"chat_id": chat_id, "user_id": user_id})
    warns = data.get("count", 0) + 1 if data else 1

    await db.warns.update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {"$set": {"count": warns}},
        upsert=True
    )
    return warns

async def get_warns(chat_id: int, user_id: int) -> int:
    data = await db.warns.find_one({"chat_id": chat_id, "user_id": user_id})
    return data.get("count", 0) if data else 0

async def reset_warns(chat_id: int, user_id: int):
    await db.warns.delete_one({"chat_id": chat_id, "user_id": user_id})

# ==========================================================
# 🧹 CLEANUP UTILS (Reset Group)
# ==========================================================

async def clear_group_data(chat_id: int):
    """Group ka saara data delete karega"""
    await db.welcome.delete_one({"chat_id": chat_id})
    await db.locks.delete_one({"chat_id": chat_id})
    await db.warns.delete_many({"chat_id": chat_id})
    await db.abuse_settings.delete_one({"chat_id": chat_id})
    await db.auth_users.delete_many({"chat_id": chat_id})
    await db.media_delete.delete_one({"chat_id": chat_id})
    await db.antibot.delete_one({"chat_id": chat_id})

# ==========================================================
# 👤 USER SYSTEM (For Broadcast)
# ==========================================================

async def add_user(user_id: int, first_name: str):
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"first_name": first_name}},
        upsert=True
    )

async def get_all_users():
    cursor = db.users.find({}, {"_id": 0, "user_id": 1})
    users = []
    async for document in cursor:
        if "user_id" in document:
            users.append(document["user_id"])
    return users

# ==========================================================
# 🛡️ AUTH & WHITELIST SYSTEM (For Anti-Nuke)
# ==========================================================

async def add_whitelist(chat_id: int, user_id: int):
    await db.auth_users.update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {"$set": {"is_auth": True}},
        upsert=True
    )

async def remove_whitelist(chat_id: int, user_id: int):
    await db.auth_users.delete_one({"chat_id": chat_id, "user_id": user_id})

async def is_user_whitelisted(chat_id: int, user_id: int) -> bool:
    data = await db.auth_users.find_one({"chat_id": chat_id, "user_id": user_id})
    return bool(data)

async def get_whitelisted_users(chat_id: int):
    cursor = db.auth_users.find({"chat_id": chat_id})
    users = []
    async for doc in cursor:
        users.append(doc["user_id"])
    return users

async def remove_all_whitelist(chat_id: int):
    await db.auth_users.delete_many({"chat_id": chat_id})

# ==========================================================
# ⏳ MEDIA AUTO-DELETE SYSTEM
# ==========================================================

async def set_media_delete_config(chat_id: int, seconds: int):
    await db.media_delete.update_one(
        {"chat_id": chat_id},
        {"$set": {"time": seconds, "enabled": True}},
        upsert=True
    )

async def set_media_delete_status(chat_id: int, status: bool):
    await db.media_delete.update_one(
        {"chat_id": chat_id},
        {"$set": {"enabled": status}},
        upsert=True
    )

async def get_media_delete_config(chat_id: int):
    """Returns: (enabled: bool, time: int)"""
    data = await db.media_delete.find_one({"chat_id": chat_id})
    if not data:
        return False, 0
    return data.get("enabled", False), data.get("time", 60)

# ==========================================================
# 🤖 ANTI-BOT SYSTEM
# ==========================================================

async def set_antibot_status(chat_id: int, status: bool):
    await db.antibot.update_one(
        {"chat_id": chat_id},
        {"$set": {"enabled": status}},
        upsert=True
    )

async def is_antibot_enabled(chat_id: int) -> bool:
    data = await db.antibot.find_one({"chat_id": chat_id})
    return data.get("enabled", False) if data else False
    
# ==========================================================
# ✏️ ANTI-EDIT SYSTEM
# ==========================================================

async def set_antiedit_status(chat_id: int, status: bool):
    await db.antiedit.update_one(
        {"chat_id": chat_id},
        {"$set": {"enabled": status}},
        upsert=True
    )

async def is_antiedit_enabled(chat_id: int) -> bool:
    data = await db.antiedit.find_one({"chat_id": chat_id})
    return data.get("enabled", False) if data else False
    
# ==========================================================
# 🧹 CLEANER SYSTEM (No Commands & No Events)
# ==========================================================

# --- No Commands ---
async def set_nocommands_status(chat_id: int, status: bool):
    await db.cleaner.update_one(
        {"chat_id": chat_id},
        {"$set": {"nocommands": status}},
        upsert=True
    )

async def is_nocommands_enabled(chat_id: int) -> bool:
    data = await db.cleaner.find_one({"chat_id": chat_id})
    return data.get("nocommands", False) if data else False

# --- No Events (Join/Left) ---
async def set_noevents_status(chat_id: int, status: bool):
    await db.cleaner.update_one(
        {"chat_id": chat_id},
        {"$set": {"noevents": status}},
        upsert=True
    )

async def is_noevents_enabled(chat_id: int) -> bool:
    data = await db.cleaner.find_one({"chat_id": chat_id})
    return data.get("noevents", False) if data else False
    
# ==========================================================
# 🛡️ ADVANCED FILTERS (Hashtags, Links, Flood, etc.)
# ==========================================================

# 1. No Hashtags
async def set_nohashtags_status(chat_id: int, status: bool):
    await db.cleaner.update_one({"chat_id": chat_id}, {"$set": {"nohashtags": status}}, upsert=True)

async def is_nohashtags_enabled(chat_id: int) -> bool:
    data = await db.cleaner.find_one({"chat_id": chat_id})
    return data.get("nohashtags", False) if data else False

# 2. Anti-Flood
async def set_antiflood_status(chat_id: int, status: bool):
    await db.cleaner.update_one({"chat_id": chat_id}, {"$set": {"antiflood": status}}, upsert=True)

async def is_antiflood_enabled(chat_id: int) -> bool:
    data = await db.cleaner.find_one({"chat_id": chat_id})
    return data.get("antiflood", False) if data else False

# 3. No Links (URLs, Mentions, Buttons)
async def set_nolinks_status(chat_id: int, status: bool):
    await db.cleaner.update_one({"chat_id": chat_id}, {"$set": {"nolinks": status}}, upsert=True)

async def is_nolinks_enabled(chat_id: int) -> bool:
    data = await db.cleaner.find_one({"chat_id": chat_id})
    return data.get("nolinks", False) if data else False

# 4. No Forwards
async def set_noforwards_status(chat_id: int, status: bool):
    await db.cleaner.update_one({"chat_id": chat_id}, {"$set": {"noforwards": status}}, upsert=True)

async def is_noforwards_enabled(chat_id: int) -> bool:
    data = await db.cleaner.find_one({"chat_id": chat_id})
    return data.get("noforwards", False) if data else False

# 5. No Contacts
async def set_nocontacts_status(chat_id: int, status: bool):
    await db.cleaner.update_one({"chat_id": chat_id}, {"$set": {"nocontacts": status}}, upsert=True)

async def is_nocontacts_enabled(chat_id: int) -> bool:
    data = await db.cleaner.find_one({"chat_id": chat_id})
    return data.get("nocontacts", False) if data else False

# 6. No Locations
async def set_nolocations_status(chat_id: int, status: bool):
    await db.cleaner.update_one({"chat_id": chat_id}, {"$set": {"nolocations": status}}, upsert=True)

async def is_nolocations_enabled(chat_id: int) -> bool:
    data = await db.cleaner.find_one({"chat_id": chat_id})
    return data.get("nolocations", False) if data else False
    
