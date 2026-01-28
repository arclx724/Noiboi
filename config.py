import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Required configurations
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# --- DATABASE FIX ---
# .env se MONGO_URI uthayega, aur usse MONGO_URL me copy kar dega
# Kyunki db.py 'MONGO_URL' dhoondh raha hai.
MONGO_URI = os.getenv("MONGO_URI", "")
MONGO_URL = MONGO_URI 

DB_NAME = os.getenv("DB_NAME", "Cluster0")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Owner and bot details
OWNER_ID = int(os.getenv("OWNER_ID", 0))
BOT_USERNAME = os.getenv("BOT_USERNAME", "NomadeHelpBot")

# Links and visuals
SUPPORT_GROUP = os.getenv("SUPPORT_GROUP", "https://t.me/RoboKaty")
UPDATE_CHANNEL = os.getenv("UPDATE_CHANNEL", "https://t.me/RoboKaty")
#START_IMAGE = os.getenv("START_IMAGE", "https://files.catbox.moe/86yrex.jpg")
