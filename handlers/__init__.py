from pyrogram import Client
import logging

# --- CONFIRMED PLUGINS (Ye aapke paas hain) ---
from .start import register_handlers as register_start
from .group_commands import register_handlers as register_group  # group -> group_commands fix
from .anti_nsfw import register_antinsfw_handlers
#from .anti_promotion import register_biolink_handlers

# --- MISSING PLUGINS (Inhe comment kar diya hai taaki error na aaye) ---
# Jab aap ye files bana lein, tab inka '#' hata dena
# from .abuse import register_handlers as register_abuse
# from .nuke import register_handlers as register_nuke
# from .media import register_handlers as register_media
# from .anti_bot import register_handlers as register_antibot
# from .edit import register_handlers as register_edit
# from .cleaner import register_handlers as register_cleaner

def register_all_handlers(app: Client):
    """
    Registers all bot modules/plugins with the Pyrogram Client.
    """
    try:
        # 1. Register Confirmed Handlers
        register_start(app)
        register_group(app)
        register_antinsfw_handlers(app)
        register_antipromo_handlers(app)
        
        # 2. Register Missing Handlers (Uncomment when files exist)
        # register_abuse(app)
        # register_nuke(app)
        # register_media(app)
        # register_antibot(app)
        # register_edit(app)
        # register_cleaner(app)
        
        logging.info("✅ Active Handlers Loaded: Start, GroupCommands, NSFW, NoPromo")
        
    except Exception as e:
        logging.error(f"❌ Error Loading Handlers: {e}")
        # Error dikhaye lekin bot crash na ho (optional)
        raise e
        
