import asyncio
import logging
from telegram.ext import Application
from config import config
from database import MongoDB
from handlers import (
    register_admin_handlers,
    register_user_handlers,
    register_moderation_handlers,
    register_message_handlers
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, config.LOG_LEVEL)
)
logger = logging.getLogger(__name__)

# Suppress verbose httpx logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)

# Application lifecycle hooks
async def post_init(application: Application):
    """Initialize bot after application is ready"""
    logger.info("Initializing bot...")
    
    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise
    
    # Connect to database
    db = MongoDB(config.MONGODB_URI, config.DATABASE_NAME)
    await db.connect()
    
    # Store database connection in bot_data
    application.bot_data['db'] = db
    
    # Restore active sessions from database
    try:
        active_sessions = await db.db.sessions.find({'is_active': True}).to_list(length=None)
        if active_sessions:
            logger.info(f"Found {len(active_sessions)} active sessions from previous run")
            for session in active_sessions:
                chat_id = session['chat_id']
                session_id = str(session['_id'])
                ad_tracking = session.get('ad_tracking_enabled', False)
                logger.info(f"  - Chat {chat_id}: Session {session_id}, Ad Tracking: {ad_tracking}")
            logger.info("All sessions are ready to continue from where they left off!")
        else:
            logger.info("No active sessions found")
    except Exception as e:
        logger.warning(f"Could not restore sessions: {e}")
    
    logger.info("Bot initialization complete!")

async def post_shutdown(application: Application):
    """Clean up before shutdown"""
    logger.info("Shutting down bot...")
    
    # Disconnect from database
    db = application.bot_data.get('db')
    if db:
        await db.disconnect()
    
    logger.info("Bot shutdown complete!")

def main():
    """Main function to run the bot"""
    logger.info("Starting Telegram Group Management Bot...")
    
    # Create application
    application = Application.builder().token(config.BOT_TOKEN).post_init(post_init).post_shutdown(post_shutdown).build()
    
    # Register all handlers
    register_admin_handlers(application)
    register_user_handlers(application)
    register_moderation_handlers(application)
    register_message_handlers(application)
    
    logger.info("All handlers registered successfully!")
    
    # Run the bot
    logger.info("Bot is now running!")
    
    if config.USE_WEBHOOK:
        # Webhook mode for Heroku
        logger.info(f"Running in webhook mode on port {config.PORT}")
        application.run_webhook(
            listen="0.0.0.0",
            port=config.PORT,
            url_path=config.BOT_TOKEN,
            webhook_url=f"{config.WEBHOOK_URL}/{config.BOT_TOKEN}"
        )
    else:
        # Polling mode for local development
        logger.info("Running in polling mode")
        application.run_polling(allowed_updates=['message', 'callback_query'])

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)
