import logging
from telegram import Update
from telegram.ext import Application, TypeHandler, ApplicationHandlerStop
from telegram.error import Conflict, NetworkError, TelegramError
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


# ──────────────────────────────────────────────
#  OWNER-ONLY PRIVATE CHAT GATE
#  Only blocks private-chat updates from non-owners.
#  Group updates pass through so group admins can use commands.
# ──────────────────────────────────────────────
async def owner_only_gate(update: Update, context) -> None:
    """Block private-chat updates from non-owner users."""
    user = update.effective_user
    if user is None:
        return  # channel posts / no sender — let pass

    chat = update.effective_chat
    # Only restrict in private chats; groups are governed per-handler
    if chat and chat.type != 'private':
        return

    if user.id != config.BOT_OWNER_ID:
        logger.debug(f"Blocked private update from non-owner {user.id} (@{user.username})")
        raise ApplicationHandlerStop


# ──────────────────────────────────────────────
#  GLOBAL ERROR HANDLER
#  Catches all unhandled exceptions from handlers
#  so they are logged cleanly instead of crashing.
# ──────────────────────────────────────────────
async def error_handler(update: object, context) -> None:
    """Handle all errors raised during update processing."""
    error = context.error

    # Conflict means another bot instance is running — log clearly
    if isinstance(error, Conflict):
        logger.critical(
            "CONFLICT ERROR: Another bot instance is already running with this token! "
            "Stop all other instances and restart. "
            f"Detail: {error}"
        )
        return

    # Network errors are transient — PTB will retry automatically
    if isinstance(error, NetworkError):
        logger.warning(f"Network error (will retry): {error}")
        return

    # Everything else — log the full traceback
    logger.error(f"Unhandled exception while processing update: {update}", exc_info=error)


# Application lifecycle hooks
async def post_init(application: Application):
    """Initialize bot after application is ready."""
    logger.info("Initializing bot...")

    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise

    # ── Delete any stale webhook so polling works without Conflict ──
    try:
        await application.bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook cleared — polling mode is clean")
    except TelegramError as e:
        logger.warning(f"Could not clear webhook (non-fatal): {e}")

    db = MongoDB(config.MONGODB_URI, config.DATABASE_NAME)
    await db.connect()
    application.bot_data['db'] = db

    # Restore active sessions
    try:
        active_sessions = await db.db.sessions.find({'is_active': True}).to_list(length=None)
        if active_sessions:
            logger.info(f"Found {len(active_sessions)} active sessions from previous run")
            for session in active_sessions:
                chat_id = session['chat_id']
                session_id = str(session['_id'])
                ad_tracking = session.get('ad_tracking_enabled', False)
                logger.info(
                    f"  - Chat {chat_id}: Session {session_id}, Ad Tracking: {ad_tracking}"
                )
        else:
            logger.info("No active sessions found")
    except Exception as e:
        logger.warning(f"Could not restore sessions: {e}")

    logger.info("Bot initialization complete!")


async def post_shutdown(application: Application):
    """Clean up before shutdown."""
    logger.info("Shutting down bot...")
    db = application.bot_data.get('db')
    if db:
        await db.disconnect()
    logger.info("Bot shutdown complete!")


def main():
    """Main function to run the bot."""
    logger.info("Starting Telegram Group Management Bot...")

    application = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Register global error handler FIRST — catches Conflict and all other errors
    application.add_error_handler(error_handler)

    # Register owner gate — only affects private chats (group=-999 runs before everything)
    application.add_handler(TypeHandler(Update, owner_only_gate), group=-999)

    register_admin_handlers(application)
    register_user_handlers(application)
    register_moderation_handlers(application)
    register_message_handlers(application)

    logger.info("All handlers registered successfully!")
    logger.info(f"Bot owner ID: {config.BOT_OWNER_ID}")
    logger.info("Bot is now running!")

    if config.USE_WEBHOOK:
        logger.info(f"Running in webhook mode on port {config.PORT}")
        application.run_webhook(
            listen="0.0.0.0",
            port=config.PORT,
            url_path=config.BOT_TOKEN,
            webhook_url=f"{config.WEBHOOK_URL}/{config.BOT_TOKEN}"
        )
    else:
        logger.info("Running in polling mode")
        application.run_polling(
            allowed_updates=['message', 'callback_query', 'edited_message'],
            drop_pending_updates=True   # discard queued updates from while bot was offline
        )


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)
