from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
import logging
import re
from config import config
from utils import extract_twitter_links, encrypt_link
from utils.fraud_detection import FraudDetector

logger = logging.getLogger(__name__)

def escape_markdown(text: str) -> str:
    """Escape special characters for Markdown"""
    # Characters that need to be escaped in Markdown
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages and track Twitter/X links"""
    if update.effective_chat.type == 'private':
        return
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    db = context.bot_data['db']
    
    # Check if group is allowed
    is_allowed = await db.is_group_allowed(chat_id)
    if not is_allowed:
        return
    
    # Check if session is active
    session = await db.get_active_session(chat_id)
    if not session or not session.get('is_active'):
        return
    
    session_id = str(session['_id'])
    
    # Get message text (from text message or caption)
    message_text = None
    if update.message.text:
        message_text = update.message.text.lower().strip()
    elif update.message.caption:
        message_text = update.message.caption.lower().strip()
    
    # Check for ad/done messages if tracking is enabled
    if message_text and await db.is_ad_tracking_enabled(chat_id):
        ad_keywords = ['ad', 'all done', 'all dn', 'done']
        
        # Check if message contains any of the keywords
        for keyword in ad_keywords:
            if keyword in message_text:
                # Check if user is already in safe list
                is_already_safe = await db.is_user_in_safe_list(chat_id, session_id, user_id)
                
                if not is_already_safe:
                    # Add to safe list
                    await db.add_to_safe_list(chat_id, session_id, user_id, username, keyword)
                    logger.info(f"Added user {username} ({user_id}) to safe list with keyword: {keyword}")
                    
                    # Mark user's links as verified (move from unsafe to safe)
                    await db.mark_user_links_verified(chat_id, user_id, session_id)
                    logger.info(f"Marked user {username} ({user_id}) links as verified")
                
                # Get user's position number in safe list
                safe_users = await db.get_safe_users(chat_id, session_id)
                user_position = next((idx + 1 for idx, u in enumerate(safe_users) if u['user_id'] == user_id), 0)
                
                # Get user's submitted link
                user_links = await db.get_user_links(chat_id, user_id, session_id)
                
                if user_links and len(user_links) > 0:
                    from utils import extract_username_from_link
                    twitter_username = extract_username_from_link(user_links[0]['link'])
                    twitter_link = user_links[0]['link']
                    
                    # Reply to user with their info - using HTML for better compatibility
                    reply_msg = (
                        f"{user_position}. 🆇 <a href='{twitter_link}'>{twitter_username}</a>\n\n"
                        f"✅ Link tracked and encrypted!"
                    )
                    
                    try:
                        # Send with HTML parse mode - more reliable than Markdown
                        await update.message.reply_text(reply_msg, parse_mode='HTML', disable_web_page_preview=True)
                    except Exception as e:
                        logger.error(f"Failed to send ad completion reply with HTML: {e}")
                        # Fallback to plain text if HTML fails
                        try:
                            plain_reply = (
                                f"{user_position}. 🆇 {twitter_username} ({twitter_link})\n\n"
                                f"✅ Link tracked and encrypted!"
                            )
                            await update.message.reply_text(plain_reply, disable_web_page_preview=True)
                        except Exception as e2:
                            logger.error(f"Failed to send ad completion message: {e2}")
                
                # Don't process further if it's just an ad message
                break
    
    # Extract Twitter/X links from message text or caption
    links = []
    if update.message.text:
        links = extract_twitter_links(update.message.text)
    elif update.message.caption:
        links = extract_twitter_links(update.message.caption)
    
    if not links:
        return
    
    # Check if user is admin - if yes, ignore their links
    from utils import is_admin
    if await is_admin(update, context):
        logger.info(f"Ignoring links from admin {username} ({user_id})")
        return
    
    # Initialize fraud detector
    fraud_detector = FraudDetector(db)
    
    # Check if user already has links submitted (before processing new links)
    existing_links = await db.get_user_links(chat_id, user_id, session_id)
    
    # If user already submitted a link, delete this message and warn them
    if len(existing_links) >= config.MAX_LINKS_PER_USER:
        try:
            await update.message.delete()
            warning_msg = (
                f"⚠️ Warning @{username}\n\n"
                f"You have already submitted {len(existing_links)} link(s). "
                f"Maximum allowed is {config.MAX_LINKS_PER_USER}.\n\n"
                f"Your message has been deleted. Multiple submissions may result in penalties."
            )
            # Send without Markdown to avoid parsing errors with special characters
            await context.bot.send_message(chat_id=chat_id, text=warning_msg)
            logger.info(f"Deleted multiple link submission from {username} ({user_id})")
        except Exception as e:
            logger.error(f"Failed to delete message or send warning: {e}")
        return
    
    for link in links:
        # Check for duplicate links (same link shared by different users)
        is_duplicate, duplicate_users = await fraud_detector.check_duplicate_link(
            chat_id, user_id, link, session_id
        )
        
        # If duplicate link detected, delete message and warn user
        if is_duplicate and config.ENABLE_FRAUD_DETECTION:
            try:
                # Delete the message with duplicate link
                await update.message.delete()
                
                # Get the original submitter info
                original_user = duplicate_users[0] if duplicate_users else None
                original_username = original_user.get('username', 'Unknown') if original_user else 'Unknown'
                
                # Send warning (same as multi-link warning)
                warning_msg = (
                    f"⚠️ Warning @{username}\n\n"
                    f"This link has already been submitted by @{original_username}.\n"
                    f"Duplicate links are not allowed.\n\n"
                    f"Your message has been deleted. Multiple submissions may result in penalties."
                )
                # Send without Markdown to avoid parsing errors with special characters
                await context.bot.send_message(chat_id=chat_id, text=warning_msg)
                logger.info(f"Deleted duplicate link from {username} ({user_id}), already submitted by {original_username}")
            except Exception as e:
                logger.error(f"Failed to delete duplicate link message: {e}")
            
            # Don't process this link further
            continue
        
        # Check if user is submitting multiple links
        exceeds_limit, current_count = await fraud_detector.check_multiple_submissions(
            chat_id, user_id, session_id, config.MAX_LINKS_PER_USER
        )
        
        # Encrypt and store link
        encrypted = encrypt_link(link)
        await db.add_link(chat_id, user_id, username, link, encrypted, session_id)
        
        # Link submitted silently - no confirmation message
        logger.info(f"Link submitted by {username} ({user_id}): {encrypted}")

def register_message_handlers(application):
    """Register all message handlers"""
    # Handle text messages
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages)
    )
    # Handle media with captions (photos, videos, documents)
    application.add_handler(
        MessageHandler((filters.PHOTO | filters.VIDEO | filters.Document.ALL) & filters.CAPTION & ~filters.COMMAND, handle_text_messages)
    )