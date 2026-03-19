from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

@dataclass
class Group:
    """Group model"""
    chat_id: int
    chat_title: str
    added_by: int
    added_at: datetime
    is_active: bool = True

@dataclass
class Session:
    """Session model"""
    chat_id: int
    created_by: int
    created_at: datetime
    is_active: bool = True
    closed_at: Optional[datetime] = None

@dataclass
class Link:
    """Link submission model"""
    chat_id: int
    user_id: int
    username: str
    link: str
    encrypted_link: str
    session_id: str
    submitted_at: datetime
    is_duplicate: bool = False
    is_verified: bool = False

@dataclass
class User:
    """User model"""
    user_id: int
    username: str
    first_name: str
    is_verified: bool = False