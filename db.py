import motor.motor_asyncio
from config import MONGO_URL

# --- DATABASE CONNECTION ---
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = client['GroupHelpClone'] 

# Collections
users_col = db['users']          # <--- MISSING COLLECTION ADDED
settings_col = db['settings']
nsfw_api_col = db['nsfw_apis']

# ======================================================
# 👤 USER MANAGEMENT (Fixed Missing Functions)
# ======================================================

async def add_user(user_id, first_name):
    """Adds a user to the database or updates their name."""
    await users_col.update_one(
        {"user_id": user_id},
        {"$set": {"first_name": first_name}},
        upsert=True
    )

async def get_all_users_count():
    """Returns the total number of bot users."""
    return await users_col.count_documents({})

# ======================================================
# 🔧 GENERAL SETTINGS HELPERS
# ======================================================

async def update_group_setting(chat_id, setting_name, value):
    """Updates a specific setting for a group."""
    await settings_col.update_one(
        {"chat_id": chat_id},
        {"$set": {setting_name: value}},
        upsert=True
    )

async def get_group_setting(chat_id, setting_name):
    """Retrieves a specific setting for a group (Default: False)."""
    doc = await settings_col.find_one({"chat_id": chat_id})
    if doc and setting_name in doc:
        return doc[setting_name]
    return False 

# ======================================================
# 👋 WELCOME SYSTEM DB
# ======================================================

async def set_welcome_status(chat_id, status: bool):
    await update_group_setting(chat_id, "welcome_enabled", status)

async def get_welcome_status(chat_id):
    return await get_group_setting(chat_id, "welcome_enabled")

async def set_welcome_message(chat_id, message: str):
    await update_group_setting(chat_id, "welcome_message", message)

async def get_welcome_message(chat_id):
    return await get_group_setting(chat_id, "welcome_message")

# ======================================================
# 🔐 LOCKS DB
# ======================================================

async def set_lock(chat_id, lock_type: str, status: bool):
    """Sets a specific lock (e.g., 'url', 'sticker') to True/False."""
    await settings_col.update_one(
        {"chat_id": chat_id},
        {"$set": {f"locks.{lock_type}": status}},
        upsert=True
    )

async def get_locks(chat_id):
    """Returns the dictionary of locks for a chat."""
    doc = await settings_col.find_one({"chat_id": chat_id})
    if doc and "locks" in doc:
        return doc["locks"]
    return {}

# ======================================================
# ⚠️ WARNINGS DB
# ======================================================

async def add_warn(chat_id, user_id):
    """Increments warn count for a user. Returns new count."""
    key = f"warns.{user_id}"
    await settings_col.update_one(
        {"chat_id": chat_id},
        {"$inc": {key: 1}},
        upsert=True
    )
    # Fetch updated count
    doc = await settings_col.find_one({"chat_id": chat_id})
    return doc.get("warns", {}).get(str(user_id), 0)

async def get_warns(chat_id, user_id):
    """Returns current warn count."""
    doc = await settings_col.find_one({"chat_id": chat_id})
    if doc and "warns" in doc:
        return doc["warns"].get(str(user_id), 0)
    return 0

async def reset_warns(chat_id, user_id):
    """Resets warns for a user to 0."""
    key = f"warns.{user_id}"
    await settings_col.update_one(
        {"chat_id": chat_id},
        {"$unset": {key: ""}}
    )

# ======================================================
# ✏️ ANTI-EDIT DB
# ======================================================

async def set_antiedit_status(chat_id, status: bool):
    await update_group_setting(chat_id, "antiedit", status)

async def is_antiedit_enabled(chat_id):
    return await get_group_setting(chat_id, "antiedit")

# ======================================================
# 🔞 ANTI-NSFW FUNCTIONS
# ======================================================

async def set_antinsfw_status(chat_id, status: bool):
    await update_group_setting(chat_id, "antinsfw", status)

async def is_antinsfw_enabled(chat_id):
    return await get_group_setting(chat_id, "antinsfw")

# --- API KEY MANAGEMENT (SightEngine) ---

async def add_nsfw_api(api_user, api_secret):
    existing = await nsfw_api_col.find_one({"api_user": api_user})
    if not existing:
        await nsfw_api_col.insert_one({
            "api_user": api_user,
            "api_secret": api_secret
        })

async def get_nsfw_api():
    """Returns a RANDOM API key to balance the load (Rotation)."""
    pipeline = [{"$sample": {"size": 1}}]
    async for doc in nsfw_api_col.aggregate(pipeline):
        return doc
    return None

async def remove_nsfw_api(api_user):
    """Removes a dead or exhausted API key."""
    await nsfw_api_col.delete_one({"api_user": api_user})

async def get_all_nsfw_apis_count():
    """Returns the total number of active keys."""
    return await nsfw_api_col.count_documents({})
    
