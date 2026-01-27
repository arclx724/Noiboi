from pyrogram import Client
import logging

# --- IMPORT OLD HANDLERS (Assuming standard function name 'register_handlers') ---
# Hum 'as' use kar rahe hain taaki naam clash na ho
from .start import register_handlers as register_start
from .group import register_handlers as register_group
from .abuse import register_handlers as register_abuse
from .nuke import register_handlers as register_nuke
from .media import register_handlers as register_media
from .anti_bot import register_handlers as register_antibot
from .edit import register_handlers as register_edit
from .cleaner import register_handlers as register_cleaner

# --- IMPORT NEW HANDLERS (Custom names) ---
from .anti_nsfw import register_antinsfw_handlers
from .anti_promotion import register_antipromo_handlers

def register_all_handlers(app: Client):
    """
    Registers all bot modules/plugins with the Pyrogram Client.
    """
    try:
        # 1. Register Old Handlers
        register_start(app)
        register_group(app)
        register_abuse(app)
        register_nuke(app)
        register_media(app)
        register_antibot(app)
        register_edit(app)
        register_cleaner(app)
        
        # 2. Register New Handlers
        register_antinsfw_handlers(app)      # SightEngine Anti-NSFW
        register_antipromo_handlers(app)     # NoPromo Anti-Promotion
        
        logging.info("✅ All Handlers Loaded Successfully: Start, Group, Abuse, Nuke, Media, Anti-Bot, Edit, Cleaner, NSFW, NoPromo")
        
    except Exception as e:
        logging.error(f"❌ Error Loading Handlers: {e}")
        # Error aane par process band na ho, isliye raise kar rahe hain taaki pata chale
        raise e
        
