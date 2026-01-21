from .start import register_handlers
from .group_commands import register_group_commands
from .anti_abuse import register_abuse_handlers

def register_all_handlers(app):
    # Register Start & Help Handlers
    register_handlers(app)
    
    # Register Group Management Handlers (Kick, Ban, Locks, etc.)
    register_group_commands(app)
    
    # Register Anti-Abuse Handlers (AI + Bad Words)
    register_abuse_handlers(app)
    
    print("✅ All handlers registered successfully!")
