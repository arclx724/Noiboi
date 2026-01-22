from .start import register_handlers
from .group_commands import register_group_commands
from .anti_abuse import register_abuse_handlers
from .anti_nuke import register_anti_nuke

def register_all_handlers(app):
    # 1. Basic Start/Help
    register_handlers(app)
    
    # 2. Group Admin Commands (Kick, Ban, Locks)
    register_group_commands(app)
    
    # 3. Anti-Abuse (Bad Words + AI)
    register_abuse_handlers(app)
    
    # 4. Anti-Nuke (Security Guard)
    register_anti_nuke(app)
    
    print("✅ All handlers (Start, Group, Abuse, Anti-Nuke) registered successfully!")
    
