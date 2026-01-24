# ============================================================
# Group Manager Bot - Database Module
# ============================================================

import motor.motor_asyncio
from config import MONGO_URI, DB_NAME
import logging
import time  # <--- Added for Anti-Nuke time calculation

# setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s'
)

try:
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    logging.info("✅ MongoDB connected successfully!")
except Exception as e:
    logging.error(f"❌ Failed to connect to MongoDB: {e}")

# ==========================================================
# 🟢 WELCOME MESSAGE SYSTEM
# ==========================================================

async def set_welcome_message(chat_id, text: str):
    await db.welcome.update_one(
        {"chat_id": chat_id},
        {"$set": {"message": text}},
        upsert=True
    )

async def get_welcome_message(chat_id):
    data = await db.welcome.find_one({"chat_id": chat_id})
    return data.get("message") if data else None

async def set_welcome_status(chat_id, status: bool):
    await db.welcome.update_one(
        {"chat_id": chat_id},
        {"$set": {"enabled": status}},
        upsert=True
    )

async def get_welcome_status(chat_id) -> bool:
    data = await db.welcome.find_one({"chat_id": chat_id})
    if not data:  # default ON
        return True
    return bool(data.get("enabled", True))

# ==========================================================
# 🔒 LOCK SYSTEM
# ==========================================================

async def set_lock(chat_id, lock_type, status: bool):
    await db.locks.update_one(
        {"chat_id": chat_id},
        {"$set": {f"locks.{lock_type}": status}},
        upsert=True
    )

async def get_locks(chat_id):
    data = await db.locks.find_one({"chat_id": chat_id})
    return data.get("locks", {}) if data else {}

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
    await db.warns.update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {"$set": {"count": 0}},
        upsert=True
    )

# ==========================================================
# 🧹 CLEANUP UTILS (Optional)
# ==========================================================

async def clear_group_data(chat_id: int):
    await db.welcome.delete_one({"chat_id": chat_id})
    await db.locks.delete_one({"chat_id": chat_id})
    await db.warns.delete_many({"chat_id": chat_id})
    await db.abuse_settings.delete_one({"chat_id": chat_id})
    await db.auth_users.delete_many({"chat_id": chat_id})
    await db.admin_limits.delete_many({"chat_id": chat_id}) # Added limits cleanup

# ==========================================================
# 👤 USER SYSTEM (for broadcast)
# ==========================================================
async def add_user(user_id, first_name):
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
# 🤬 ABUSE & AUTH SYSTEM
# ==========================================================

async def is_abuse_enabled(chat_id: int) -> bool:
    data = await db.abuse_settings.find_one({"chat_id": chat_id})
    return data.get("enabled", False) if data else False

async def set_abuse_status(chat_id: int, enabled: bool):
    await db.abuse_settings.update_one(
        {"chat_id": chat_id},
        {"$set": {"enabled": enabled}},
        upsert=True
    )

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
    # Returns a list of user_ids
    cursor = db.auth_users.find({"chat_id": chat_id})
    users = []
    async for doc in cursor:
        users.append(doc["user_id"])
    return users

async def remove_all_whitelist(chat_id: int):
    await db.auth_users.delete_many({"chat_id": chat_id})

# ==========================================================
# ☢️ ANTI-NUKE SYSTEM (NEW ADDED)
# ==========================================================

async def check_admin_limit(chat_id: int, user_id: int, limit: int = 10):
    """
    Check karega ki admin ne aaj limit cross ki hai ya nahi.
    Returns: (Allowed: bool, Current_Count: int)
    """
    current_time = time.time()
    
    # Record find karo (Admin Limits Collection mein)
    record = await db.admin_limits.find_one({"chat_id": chat_id, "user_id": user_id})
    
    if record:
        # Reset Time Check (24 Hours = 86400 seconds)
        if current_time > record.get('reset_time', 0):
            # Limit Reset karo
            await db.admin_limits.update_one(
                {"_id": record['_id']},
                {"$set": {"count": 1, "reset_time": current_time + 86400}}
            )
            return True, 1
            
        # Agar Time Valid hai, to Count check karo
        elif record['count'] < limit:
            # Count badhao
            await db.admin_limits.update_one(
                {"_id": record['_id']},
                {"$inc": {"count": 1}}
            )
            return True, record['count'] + 1
            
        # Agar Limit Cross ho gayi
        else:
            return False, limit
    else:
        # Pehli baar entry (New Record)
        await db.admin_limits.insert_one({
            "chat_id": chat_id, 
            "user_id": user_id, 
            "count": 1, 
            "reset_time": current_time + 86400
        })
        return True, 1

async def reset_admin_limit(chat_id: int):
    """Poore group ki limits reset karega (Owner Command)"""
    await db.admin_limits.delete_many({"chat_id": chat_id})
    
# ==========================================================
# 🧹 CLEAN SERVICE SYSTEM (Service Message Deleter)
# ==========================================================

async def enable_clean_service(chat_id: int, service_type: str):
    """Specific service type ko clean list mein add karega"""
    if service_type == "all":
        # Agar 'all' select kiya, to purana sab hata ke sirf 'all' set karo
        await db.clean_service.update_one(
            {"chat_id": chat_id},
            {"$set": {"types": ["all"]}},
            upsert=True
        )
    else:
        # Pehle check karo agar 'all' already set hai to usse hatao (specific control ke liye)
        await db.clean_service.update_one(
            {"chat_id": chat_id},
            {"$pull": {"types": "all"}}
        )
        # Ab specific type add karo
        await db.clean_service.update_one(
            {"chat_id": chat_id},
            {"$addToSet": {"types": service_type}},
            upsert=True
        )

async def disable_clean_service(chat_id: int, service_type: str):
    """Specific service type ko clean list se hatayega"""
    if service_type == "all":
        # 'all' hatane ka matlab sab kuch disable karna
        await db.clean_service.delete_one({"chat_id": chat_id})
    else:
        # Agar 'all' enabled tha, to use hata kar baaki sab add karne padenge (logic complex hai, simple rakhte hain)
        # Simple Logic: Just remove the tag.
        await db.clean_service.update_one(
            {"chat_id": chat_id},
            {"$pull": {"types": service_type}}
        )
        # Note: Agar 'all' set tha aur user ne '/keepservice join' kiya, 
        # to technically 'all' hat jana chahiye aur baaki sab rehne chahiye. 
        # Par abhi ke liye simple rakhte hain: 'all' hata do.
        await db.clean_service.update_one(
            {"chat_id": chat_id},
            {"$pull": {"types": "all"}}
        )

async def get_clean_service_types(chat_id: int) -> list:
    """Check karega kaunse messages delete karne hain"""
    data = await db.clean_service.find_one({"chat_id": chat_id})
    return data.get("types", []) if data else []
    
