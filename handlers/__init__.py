from .start import register_handlers
from .group_commands import register_group_commands
from .anti_abuse import register_abuse_handlers
from .anti_nuke import register_anti_nuke
from .media_delete import register_media_delete_handlers
from .anti_bots import register_antibot_handlers
from .anti_edit import register_antiedit_handlers
from .cleaner import register_cleaner_handlers
from .anti_nsfw import register_antinsfw_handlers

def register_all_handlers(app):
    register_handlers(app)
    register_group_commands(app)
    register_abuse_handlers(app)
    register_anti_nuke(app)
    register_media_delete_handlers(app)
    register_antibot_handlers(app)
    register_antiedit_handlers(app)
    register_cleaner_handlers(app)
    register_antinsfw_handlers(app)
    
    print("✅ All Handlers Loaded: Start, Group, Abuse, Nuke, Media, Anti-Bot, Edit, Cleaner, NSFW")
    
