from .start import register_handlers
from .group_commands import register_group_commands
from .anti_abuse import register_abuse_handlers
from .anti_nuke import register_anti_nuke
from .clean_service import register_clean_service_handlers
from .media_delete import register_media_delete_handlers  # <--- NEW IMPORT

def register_all_handlers(app):
    register_handlers(app)
    register_group_commands(app)
    register_abuse_handlers(app)
    register_anti_nuke(app)
    register_clean_service_handlers(app)
    
    # Register New Plugin
    register_media_delete_handlers(app)  # <--- NEW CALL
    
    print("✅ All Handlers Loaded: Start, Group, Abuse, Anti-Nuke, Clean-Service, Media-Delete")
    
