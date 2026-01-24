from .start import register_handlers
from .group_commands import register_group_commands
from .anti_abuse import register_abuse_handlers
from .anti_nuke import register_anti_nuke
from .clean_service import register_clean_service_handlers  # <--- NEW IMPORT

def register_all_handlers(app):
    # 1. Start & Help
    register_handlers(app)
    
    # 2. Group Admin Commands
    register_group_commands(app)
    
    # 3. Anti-Abuse System
    register_abuse_handlers(app)
    
    # 4. Anti-Nuke System
    register_anti_nuke(app)
    
    # 5. Clean Service System (NEW)
    register_clean_service_handlers(app)  # <--- NEW REGISTRATION
    
    print("✅ All Handlers Loaded: Start, Group, Abuse, Anti-Nuke, Clean-Service")
    
