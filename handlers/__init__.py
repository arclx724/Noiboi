from .start import register_handlers
from .group_commands import register_group_commands
from .anti_abuse import register_abuse_handlers
from .anti_nuke import register_anti_nuke

def register_all_handlers(app):
    # 1. Register Basic Handlers (Start, Help)
    register_handlers(app)
    
    # 2. Register Group Admin Commands (Kick, Ban, Locks, Welcome)
    register_group_commands(app)
    
    # 3. Register Anti-Abuse System (AI + Bad Words Filter)
    register_abuse_handlers(app)
    
    # 4. Register Anti-Nuke System (Admin Limit & Auto-Demote)
    register_anti_nuke(app)
    
    print("✅ All Modules (Start, Group, Abuse, Anti-Nuke) Registered Successfully!")
    
