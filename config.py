import os
from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    """Get a required env var — crash with a clear message if missing."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}\n"
            f"Set it in your .env file or in your hosting platform's env config."
        )
    return value


class Config:
    """Configuration management for the bot — all values come from environment variables."""

    # Telegram Bot Configuration
    BOT_TOKEN: str = os.getenv('BOT_TOKEN', '')
    API_ID: int = int(os.getenv('API_ID', '0'))
    API_HASH: str = os.getenv('API_HASH', '')

    # MongoDB Configuration
    MONGODB_URI: str = os.getenv('MONGODB_URI', '')
    DATABASE_NAME: str = os.getenv('DATABASE_NAME', 'group_manager')

    # Bot Owner Configuration
    BOT_OWNER_ID: int = int(os.getenv('BOT_OWNER_ID', '0'))

    # Webhook Configuration (for Heroku/Northflank deployment)
    WEBHOOK_URL: str = os.getenv('WEBHOOK_URL', '')
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
        """Validate that all required configuration values are present."""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required — set it in .env or hosting env vars")
        if not cls.MONGODB_URI:
            raise ValueError("MONGODB_URI is required — set it in .env or hosting env vars")
        if cls.BOT_OWNER_ID == 0:
            raise ValueError("BOT_OWNER_ID is required — set it in .env or hosting env vars")
        if cls.USE_WEBHOOK and not cls.WEBHOOK_URL:
            raise ValueError("WEBHOOK_URL is required when USE_WEBHOOK is true")
        return True


config = Config()
