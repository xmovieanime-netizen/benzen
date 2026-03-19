from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MongoDB:
    """MongoDB connection and operations handler"""
    
    def __init__(self, uri: str, database_name: str):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.uri = uri
        self.database_name = database_name
    
    async def connect(self):
        """Establish MongoDB connection"""
        try:
            self.client = AsyncIOMotorClient(self.uri)
            self.db = self.client[self.database_name]
            # Test connection
            await self.client.admin.command('ping')
            logger.info("Connected to MongoDB successfully")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    # ========== Group Operations ==========
    
    async def add_allowed_group(self, chat_id: int, chat_title: str, added_by: int) -> bool:
        """Add a group to allowed list"""
        try:
            await self.db.allowed_groups.update_one(
                {'chat_id': chat_id},
                {
                    '$set': {
                        'chat_id': chat_id,
                        'chat_title': chat_title,
                        'added_by': added_by,
                        'added_at': datetime.utcnow(),
                        'is_active': True
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error adding group: {e}")
            return False
    
    async def remove_allowed_group(self, chat_id: int) -> bool:
        """Remove a group from allowed list"""
        try:
            result = await self.db.allowed_groups.delete_one({'chat_id': chat_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error removing group: {e}")
            return False
    
    async def is_group_allowed(self, chat_id: int) -> bool:
        """Check if group is allowed"""
        try:
            group = await self.db.allowed_groups.find_one({
                'chat_id': chat_id,
                'is_active': True
            })
            return group is not None
        except Exception as e:
            logger.error(f"Error checking group: {e}")
            return False
    
    async def get_all_allowed_groups(self) -> List[Dict[str, Any]]:
        """Get all allowed groups"""
        try:
            cursor = self.db.allowed_groups.find({'is_active': True})
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"Error fetching groups: {e}")
            return []
    
    # ========== Session Operations ==========
    
    async def create_session(self, chat_id: int, created_by: int) -> str:
        """Create a new group session"""
        try:
            session = {
                'chat_id': chat_id,
                'created_by': created_by,
                'created_at': datetime.utcnow(),
                'is_active': True,
                'closed_at': None
            }
            result = await self.db.sessions.insert_one(session)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return None
    
    async def get_active_session(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Get active session for a group"""
        try:
            return await self.db.sessions.find_one({
                'chat_id': chat_id,
                'is_active': True
            })
        except Exception as e:
            logger.error(f"Error fetching session: {e}")
            return None
    
    async def close_session(self, chat_id: int) -> bool:
        """Close active session"""
        try:
            result = await self.db.sessions.update_one(
                {'chat_id': chat_id, 'is_active': True},
                {
                    '$set': {
                        'is_active': False,
                        'closed_at': datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error closing session: {e}")
            return False
    
    async def reopen_session(self, chat_id: int) -> bool:
        """Reopen last closed session"""
        try:
            result = await self.db.sessions.update_one(
                {'chat_id': chat_id, 'is_active': False},
                {'$set': {'is_active': True}},
                sort=[('closed_at', -1)]
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error reopening session: {e}")
            return False
    
    # ========== Link Operations ==========
    
    async def add_link(self, chat_id: int, user_id: int, username: str, 
                       link: str, encrypted_link: str, session_id: str) -> bool:
        """Add a link submission"""
        try:
            link_doc = {
                'chat_id': chat_id,
                'user_id': user_id,
                'username': username,
                'link': link,
                'encrypted_link': encrypted_link,
                'session_id': session_id,
                'submitted_at': datetime.utcnow(),
                'is_duplicate': False,
                'is_verified': False
            }
            await self.db.links.insert_one(link_doc)
            return True
        except Exception as e:
            logger.error(f"Error adding link: {e}")
            return False
    
    async def get_user_links(self, chat_id: int, user_id: int, session_id: str) -> List[Dict[str, Any]]:
        """Get all links for a user in current session"""
        try:
            cursor = self.db.links.find({
                'chat_id': chat_id,
                'user_id': user_id,
                'session_id': session_id
            })
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"Error fetching user links: {e}")
            return []
    
    async def get_duplicate_links(self, chat_id: int, link: str, session_id: str) -> List[Dict[str, Any]]:
        """Find users who shared the same link"""
        try:
            cursor = self.db.links.find({
                'chat_id': chat_id,
                'link': link,
                'session_id': session_id
            })
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"Error checking duplicates: {e}")
            return []
    
    async def get_users_with_multiple_links(self, chat_id: int, session_id: str) -> List[Dict[str, Any]]:
        """Get users who submitted multiple links"""
        try:
            pipeline = [
                {
                    '$match': {
                        'chat_id': chat_id,
                        'session_id': session_id
                    }
                },
                {
                    '$group': {
                        '_id': '$user_id',
                        'username': {'$first': '$username'},
                        'count': {'$sum': 1},
                        'links': {'$push': '$link'}
                    }
                },
                {
                    '$match': {
                        'count': {'$gt': 1}
                    }
                }
            ]
            cursor = self.db.links.aggregate(pipeline)
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"Error fetching multi-link users: {e}")
            return []
    
    async def mark_link_as_duplicate(self, link_id: str) -> bool:
        """Mark a link as duplicate"""
        try:
            from bson import ObjectId
            result = await self.db.links.update_one(
                {'_id': ObjectId(link_id)},
                {'$set': {'is_duplicate': True}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error marking duplicate: {e}")
            return False
    
    async def get_session_stats(self, chat_id: int, session_id: str) -> Dict[str, int]:
        """Get statistics for current session"""
        try:
            total_links = await self.db.links.count_documents({
                'chat_id': chat_id,
                'session_id': session_id
            })
            
            unique_users = len(await self.db.links.distinct('user_id', {
                'chat_id': chat_id,
                'session_id': session_id
            }))
            
            verified_count = await self.db.links.count_documents({
                'chat_id': chat_id,
                'session_id': session_id,
                'is_verified': True
            })
            
            return {
                'total_links': total_links,
                'unique_users': unique_users,
                'verified_users': verified_count
            }
        except Exception as e:
            logger.error(f"Error fetching stats: {e}")
            return {'total_links': 0, 'unique_users': 0, 'verified_users': 0}
    
    async def get_all_users_with_links(self, chat_id: int, session_id: str) -> List[Dict[str, Any]]:
        """Get all users with their submitted links for the session"""
        try:
            pipeline = [
                {
                    '$match': {
                        'chat_id': chat_id,
                        'session_id': session_id
                    }
                },
                {
                    '$group': {
                        '_id': '$user_id',
                        'user_id': {'$first': '$user_id'},
                        'username': {'$first': '$username'},
                        'links': {'$push': '$link'},
                        'is_verified': {'$first': '$is_verified'},
                        'submitted_at': {'$first': '$submitted_at'}
                    }
                },
                {
                    '$sort': {'submitted_at': 1}
                }
            ]
            cursor = self.db.links.aggregate(pipeline)
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"Error fetching users with links: {e}")
            return []
    
    # ========== User Operations ==========
    
    async def add_to_sr_list(self, chat_id: int, user_id: int, username: str) -> bool:
        """Add user to screen recording request list"""
        try:
            await self.db.sr_requests.update_one(
                {'chat_id': chat_id, 'user_id': user_id},
                {
                    '$set': {
                        'chat_id': chat_id,
                        'user_id': user_id,
                        'username': username,
                        'requested_at': datetime.utcnow(),
                        'is_completed': False
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error adding to SR list: {e}")
            return False
    
    async def get_sr_list(self, chat_id: int) -> List[Dict[str, Any]]:
        """Get screen recording request list"""
        try:
            cursor = self.db.sr_requests.find({
                'chat_id': chat_id,
                'is_completed': False
            })
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"Error fetching SR list: {e}")
            return []
    
    async def add_to_ad_list(self, chat_id: int, user_id: int, username: str) -> bool:
        """Add user to ad list"""
        try:
            await self.db.ad_list.update_one(
                {'chat_id': chat_id, 'user_id': user_id},
                {
                    '$set': {
                        'chat_id': chat_id,
                        'user_id': user_id,
                        'username': username,
                        'added_at': datetime.utcnow()
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error adding to ad list: {e}")
            return False
    
    async def clear_session_data(self, chat_id: int, session_id: str) -> bool:
        """Clear all data for a session"""
        try:
            await self.db.links.delete_many({
                'chat_id': chat_id,
                'session_id': session_id
            })
            await self.db.sr_requests.delete_many({'chat_id': chat_id})
            return True
        except Exception as e:
            logger.error(f"Error clearing session data: {e}")
            return False
    
    # ========== Ad Tracking Operations ==========
    
    async def enable_ad_tracking(self, chat_id: int, session_id: str) -> bool:
        """Enable ad tracking for a session"""
        try:
            result = await self.db.sessions.update_one(
                {'chat_id': chat_id, 'is_active': True},
                {'$set': {'ad_tracking_enabled': True}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error enabling ad tracking: {e}")
            return False
    
    async def is_ad_tracking_enabled(self, chat_id: int) -> bool:
        """Check if ad tracking is enabled for the current session"""
        try:
            session = await self.get_active_session(chat_id)
            if not session:
                return False
            return session.get('ad_tracking_enabled', False)
        except Exception as e:
            logger.error(f"Error checking ad tracking: {e}")
            return False
    
    async def add_to_safe_list(self, chat_id: int, session_id: str, user_id: int, 
                               username: str, ad_text: str) -> bool:
        """Add user to safe list (users who sent ad/done messages)"""
        try:
            await self.db.safe_list.update_one(
                {
                    'chat_id': chat_id,
                    'session_id': session_id,
                    'user_id': user_id
                },
                {
                    '$set': {
                        'chat_id': chat_id,
                        'session_id': session_id,
                        'user_id': user_id,
                        'username': username,
                        'ad_text': ad_text,
                        'added_at': datetime.utcnow()
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error adding to safe list: {e}")
            return False
    
    async def get_safe_users(self, chat_id: int, session_id: str) -> List[Dict[str, Any]]:
        """Get all users in safe list for the session"""
        try:
            cursor = self.db.safe_list.find({
                'chat_id': chat_id,
                'session_id': session_id
            }).sort('added_at', 1)
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"Error fetching safe list: {e}")
            return []
    
    async def is_user_in_safe_list(self, chat_id: int, session_id: str, user_id: int) -> bool:
        """Check if user is already in safe list"""
        try:
            user = await self.db.safe_list.find_one({
                'chat_id': chat_id,
                'session_id': session_id,
                'user_id': user_id
            })
            return user is not None
        except Exception as e:
            logger.error(f"Error checking safe list: {e}")
            return False
    
    async def mark_user_links_verified(self, chat_id: int, user_id: int, session_id: str) -> bool:
        """Mark all user's links as verified (move from unsafe to safe)"""
        try:
            result = await self.db.links.update_many(
                {
                    'chat_id': chat_id,
                    'user_id': user_id,
                    'session_id': session_id
                },
                {'$set': {'is_verified': True}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error marking links as verified: {e}")
            return False
