import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration management for the bot"""
    
    # Telegram Bot Configuration
    BOT_TOKEN: str = os.getenv('BOT_TOKEN', '8657533291:AAGW8yv0MxgIWJ4gFidVPC8F7Ufd7LpfVbk')
    API_ID: int = int(os.getenv('API_ID', '28271319'))
    API_HASH: str = os.getenv('API_HASH', '84d8b635a127218158581c0fd8225770')
    
    # MongoDB Configuration
    MONGODB_URI: str = os.getenv('MONGODB_URI', 'mongodb+srv://Capture:capture@cluster0.7jqepnf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
    DATABASE_NAME: str = os.getenv('DATABASE_NAME', 'group_manager')
    
    # Bot Owner Configuration
    BOT_OWNER_ID: int = int(os.getenv('BOT_OWNER_ID', '6178527968'))
    
    # Webhook Configuration (for Heroku/Northflank deployment)
    WEBHOOK_URL: str = os.getenv('WEBHOOK_URL', '')  # e.g., https://yourapp.herokuapp.com
    PORT: int = int(os.getenv('PORT', '8443'))
    USE_WEBHOOK: bool = os.getenv('USE_WEBHOOK', 'false').lower() == 'true'
    
    # Feature Flags
    ENABLE_FRAUD_DETECTION: bool = os.getenv('ENABLE_FRAUD_DETECTION', 'true').lower() == 'true'
    ENABLE_AUTO_WARNINGS: bool = os.getenv('ENABLE_AUTO_WARNINGS', 'true').lower() == 'true'
    
    # Limits
    MAX_LINKS_PER_USER: int = int(os.getenv('MAX_LINKS_PER_USER', '1'))
    DEFAULT_MUTE_DURATION: int = int(os.getenv('DEFAULT_MUTE_DURATION', '3'))  # days
    
    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")
        if not cls.MONGODB_URI:
            raise ValueError("MONGODB_URI is required")
        if cls.BOT_OWNER_ID == 0:
            raise ValueError("BOT_OWNER_ID is required")
        if cls.USE_WEBHOOK and not cls.WEBHOOK_URL:
            raise ValueError("WEBHOOK_URL is required when USE_WEBHOOK is true")
        return True


config = Config()

