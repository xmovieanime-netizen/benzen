import re
import hashlib
import logging
from datetime import timedelta
from typing import List
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus

logger = logging.getLogger(__name__)

def encrypt_link(link: str) -> str:
    """Encrypt Twitter/X link using SHA-256"""
    return hashlib.sha256(link.encode()).hexdigest()[:16]

def parse_duration(duration_str: str) -> timedelta:
    """
    Parse duration string like '2d 5h 30m 10s' into timedelta
    Returns default 3 days if invalid or empty
    """
    if not duration_str:
        return timedelta(days=3)
    
    total_seconds = 0
    pattern = r'(\d+)\s*([dhms]|day|days|hour|hours|minute|minutes|second|seconds)'
    matches = re.findall(pattern, duration_str.lower())
    
    for value, unit in matches:
        value = int(value)
        if unit in ['d', 'day', 'days']:
            total_seconds += value * 86400
        elif unit in ['h', 'hour', 'hours']:
            total_seconds += value * 3600
        elif unit in ['m', 'minute', 'minutes']:
            total_seconds += value * 60
        elif unit in ['s', 'second', 'seconds']:
            total_seconds += value
    
    return timedelta(seconds=total_seconds) if total_seconds > 0 else timedelta(days=3)

def extract_twitter_links(text: str) -> List[str]:
    """Extract Twitter/X links from text"""
    if not text:
        return []
    
    patterns = [
        r'https?://(?:www\.)?twitter\.com/[^\s]+',
        r'https?://(?:www\.)?x\.com/[^\s]+',
        r'https?://t\.co/[^\s]+'
    ]
    
    links = []
    for pattern in patterns:
        found = re.findall(pattern, text)
        links.extend(found)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_links = []
    for link in links:
        if link not in seen:
            seen.add(link)
            unique_links.append(link)
    
    return unique_links

def extract_username_from_link(link: str) -> str:
    """Extract username from Twitter/X link"""
    patterns = [
        r'twitter\.com/([^/\s?]+)',
        r'x\.com/([^/\s?]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, link)
        if match:
            return match.group(1)
    
    return "unknown"

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is admin in the group"""
    if update.effective_chat.type == 'private':
        return True
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        # Check for both old and new attribute names for compatibility
        is_admin_status = member.status in [
            ChatMemberStatus.OWNER,  # New name in python-telegram-bot v20+
            ChatMemberStatus.ADMINISTRATOR
        ]
        logger.info(f"Admin check for user {user_id} in chat {chat_id}: status={member.status}, is_admin={is_admin_status}")
        return is_admin_status
    except AttributeError as e:
        logger.error(f"AttributeError in admin check: {e}. Using string comparison fallback.")
        # Fallback to string comparison if attributes don't exist
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            is_admin_status = member.status in ['creator', 'administrator']
            logger.info(f"Admin check (fallback) for user {user_id}: status={member.status}, is_admin={is_admin_status}")
            return is_admin_status
        except Exception as e2:
            logger.error(f"Fallback admin check also failed: {e2}")
            return True
    except Exception as e:
        logger.error(f"Error checking admin status for user {user_id} in chat {chat_id}: {e}")
        # If we can't check (e.g., bot is not admin), assume user might be admin
        # This happens when bot doesn't have permission to get chat member info
        logger.warning(f"Returning True by default - bot may need admin permissions in chat {chat_id}")
        return True

def format_user_mention(user_id: int, username: str = None, first_name: str = None) -> str:
    """Format user mention for messages"""
    if username:
        return f"@{username}"
    elif first_name:
        return f"[{first_name}](tg://user?id={user_id})"
    else:
        return f"User {user_id}"

def escape_html(text: str) -> str:
    """Escape HTML special characters to prevent parsing errors"""
    if not text:
        return text
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#x27;'))