import motor.motor_asyncio
from config import MONGO_URL

# --- DATABASE CONNECTION ---
# Motor is used for Asynchronous MongoDB (Fast & Non-blocking)
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = client['GroupHelpClone'] 

# Collections
settings_col = db['settings']
nsfw_api_col = db['nsfw_apis']

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
# 🔞 ANTI-NSFW FUNCTIONS
# ======================================================

async def set_antinsfw_status(chat_id, status: bool):
    await update_group_setting(chat_id, "antinsfw", status)

async def is_antinsfw_enabled(chat_id):
    return await get_group_setting(chat_id, "antinsfw")

# --- API KEY MANAGEMENT (SightEngine) ---

async def add_nsfw_api(api_user, api_secret):
    # Check if key already exists to prevent duplicates
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

# ======================================================
# ⛔ ANTI-PROMOTION FUNCTIONS
# ======================================================

async def set_antipromo_status(chat_id, status: bool):
    await update_group_setting(chat_id, "antipromo", status)

async def is_antipromo_enabled(chat_id):
    return await get_group_setting(chat_id, "antipromo")
    
