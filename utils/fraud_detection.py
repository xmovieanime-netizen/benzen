from typing import List, Dict, Set, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FraudDetector:
    """Detect fraudulent behavior in link submissions"""
    
    def __init__(self, db):
        self.db = db
    
    async def check_duplicate_link(self, chat_id: int, user_id: int, 
                                   link: str, session_id: str) -> Tuple[bool, List[Dict]]:
        """
        Check if link has been shared by other users
        Returns (is_duplicate, list_of_users_with_same_link)
        """
        duplicates = await self.db.get_duplicate_links(chat_id, link, session_id)
        
        # Filter out current user
        other_users = [d for d in duplicates if d['user_id'] != user_id]
        
        if other_users:
            logger.warning(f"Duplicate link detected: {link} in chat {chat_id}")
            return True, other_users
        
        return False, []
    
    async def check_multiple_submissions(self, chat_id: int, user_id: int, 
                                        session_id: str, max_allowed: int = 1) -> Tuple[bool, int]:
        """
        Check if user has submitted multiple links
        Returns (exceeds_limit, current_count)
        """
        user_links = await self.db.get_user_links(chat_id, user_id, session_id)
        count = len(user_links)
        
        if count > max_allowed:
            logger.warning(f"User {user_id} exceeded link limit: {count}/{max_allowed}")
            return True, count
        
        return False, count
    
    async def generate_fraud_alert(self, chat_id: int, link: str, 
                                   session_id: str) -> str:
        """Generate fraud alert message for duplicate links"""
        from .helpers import extract_username_from_link
        
        duplicates = await self.db.get_duplicate_links(chat_id, link, session_id)
        
        if len(duplicates) < 2:
            return ""
        
        # Extract account username from link
        account_username = extract_username_from_link(link)
        
        # Get suspicious usernames
        suspicious_users = [d['username'] for d in duplicates if d.get('username')]
        
        alert = f"""🚨 *Fraud Alert*
        
Multiple users are sharing the same X account link: *{account_username}*

Suspicious users: {', '.join(suspicious_users[:5])}

⚠️ This behavior is suspicious and will be monitored."""
        
        return alert
    
    async def get_fraud_statistics(self, chat_id: int, session_id: str) -> Dict[str, int]:
        """Get fraud statistics for current session"""
        try:
            # Count duplicate submissions
            duplicates = await self.db.links.count_documents({
                'chat_id': chat_id,
                'session_id': session_id,
                'is_duplicate': True
            })
            
            # Count users with multiple links
            multi_link_users = await self.db.get_users_with_multiple_links(chat_id, session_id)
            
            return {
                'duplicate_submissions': duplicates,
                'users_with_multiple_links': len(multi_link_users)
            }
        except Exception as e:
            logger.error(f"Error getting fraud stats: {e}")
            return {'duplicate_submissions': 0, 'users_with_multiple_links': 0}