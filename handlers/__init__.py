
from .admin import register_admin_handlers
from .user import register_user_handlers
from .moderation import register_moderation_handlers
from .messages import register_message_handlers

__all__ = [
    'register_admin_handlers',
    'register_user_handlers',
    'register_moderation_handlers',
    'register_message_handlers'
]
