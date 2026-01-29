# ============================================================
# Group Manager Bot
# ============================================================

from pyrogram import Client, idle  # <--- idle ko import karna zaroori hai
from config import API_ID, API_HASH, BOT_TOKEN
import logging
from handlers import register_all_handlers
import asyncio

# Logging setup (Errors dekhne ke liye)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Client Setup
app = Client(
    "group_manger_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Handlers Register karna
register_all_handlers(app)

# --- Nayi Startup Logic (Zyada Stable) ---
async def main():
    try:
        print("Connecting to Telegram...")
        await app.start()
        
        # Bot ki info print karega (Confirm karne ke liye ki login ho gaya)
        me = await app.get_me()
        print(f"✅ Bot Started Successfully: @{me.username}")
        
        # Ye line bot ko band hone se rokegi jab tak aap stop na karein
        await idle()
        
    except Exception as e:
        print(f"❌ Error during startup: {e}")
    finally:
        # Jab bot band hoga toh ye chalega
        await app.stop()
        print("Bot Stopped.")

if __name__ == "__main__":
    # Event Loop start karna
    app.run(main())
