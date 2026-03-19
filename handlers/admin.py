from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
import logging
from config import config
from utils import is_admin

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    chat_type = update.effective_chat.type
    db = context.bot_data['db']
    
    if chat_type == 'private':
        await update.message.reply_text(
            "👋 *Welcome to Group Management Bot!*\n\n"
            "I help manage Telegram groups by:\n"
            "✅ Tracking and encrypting shared Twitter/X links\n"
            "✅ Detecting fraud and duplicate submissions\n"
            "✅ Managing user verification\n"
            "✅ Muting or warning rule-breakers\n\n"
            "Add me to your group and use /help to see all commands!\n\n"
            "🔧 *Bot Owner Commands:*\n"
            "/managegroups - Configure allowed groups",
            parse_mode='Markdown'
        )
    else:
        # Check if group is allowed
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        
        logger.info(f"Start command in group {chat_id} by user {user_id} ({username})")
        
        # Check if user is admin
        admin_check = await is_admin(update, context)
        logger.info(f"Admin check result for user {user_id}: {admin_check}")
        
        if not admin_check:
            await update.message.reply_text(
                "❌ Only admins can activate the bot!"
            )
            return
        
        is_allowed = await db.is_group_allowed(chat_id)
        
        if not is_allowed:
            await update.message.reply_text(
                "⚠️ This group is not authorized!\n\n"
                "Please contact the bot owner to add this group to the allowed list.\n"
                f"Group ID: `{chat_id}`",
                parse_mode='Markdown'
            )
            return
        
        # Create session
        session = await db.get_active_session(chat_id)
        if not session:
            session_id = await db.create_session(chat_id, update.effective_user.id)
            if session_id:
                # Unlock the group to allow messaging
                try:
                    permissions = ChatPermissions(
                        can_send_messages=True,
                        can_send_audios=True,
                        can_send_documents=True,
                        can_send_photos=True,
                        can_send_videos=True,
                        can_send_video_notes=True,
                        can_send_voice_notes=True,
                        can_send_polls=True,
                        can_send_other_messages=True,
                        can_add_web_page_previews=True,
                        can_change_info=False,
                        can_invite_users=True,
                        can_pin_messages=False
                    )
                    await context.bot.set_chat_permissions(chat_id, permissions)
                    logger.info(f"Group {chat_id} unlocked - session started")
                except Exception as e:
                    logger.warning(f"Could not set chat permissions: {e}")
                
                # Send video with caption
                try:
                    await context.bot.send_video(
                        chat_id=chat_id,
                        video="https://envs.sh/M-h.mp4",
                        caption=(
                            "✅ *Group session activated!*\n\n"
                            "The bot is now tracking link submissions.\n"
                            "🔓 Group is unlocked - all users can message."
                        ),
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Failed to send video: {e}")
                    # Fallback to text message if video fails
                    await update.message.reply_text(
                        "✅ *Group session activated!*\n\n"
                        "The bot is now tracking link submissions.\n"
                        "🔓 Group is unlocked - all users can message.",
                        parse_mode='Markdown'
                    )
            else:
                await update.message.reply_text("❌ Failed to create session!")
        else:
            # Session already exists, make sure group is unlocked
            try:
                permissions = ChatPermissions(
                    can_send_messages=True,
                    can_send_audios=True,
                    can_send_documents=True,
                    can_send_photos=True,
                    can_send_videos=True,
                    can_send_video_notes=True,
                    can_send_voice_notes=True,
                    can_send_polls=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                    can_change_info=False,
                    can_invite_users=True,
                    can_pin_messages=False
                )
                await context.bot.set_chat_permissions(chat_id, permissions)
                logger.info(f"Group {chat_id} unlocked - session already active")
            except Exception as e:
                logger.warning(f"Could not set chat permissions: {e}")
            
            await update.message.reply_text(
                "✅ Session already active!!\n"
                "🔓 Group is unlocked - all users can message."
            )

async def starts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /starts command for groups (alias for /start)"""
    await start_command(update, context)

async def refresh_admins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Refresh admin list for the group"""
    if update.effective_chat.type == 'private':
        await update.message.reply_text("This command is only available in groups!")
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("❌ This command is only for admins!")
        return
    
    chat_id = update.effective_chat.id
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        admin_count = len(admins)
        await update.message.reply_text(
            f"✅ Admin list refreshed!\n📊 Found *{admin_count}* admins.",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error refreshing admins: {e}")
        await update.message.reply_text(f"❌ Error refreshing admins: {str(e)}")

async def close_session_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lock the group without ending the session"""
    if update.effective_chat.type == 'private':
        await update.message.reply_text("This command is only available in groups!")
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("❌ This command is only for admins!")
        return
    
    chat_id = update.effective_chat.id
    db = context.bot_data['db']
    
    # Check if there's an active session
    session = await db.get_active_session(chat_id)
    if not session:
        await update.message.reply_text("❌ No active session! Use /start to begin.")
        return
    
    # Lock the group (don't end the session)
    try:
        permissions = ChatPermissions(
            can_send_messages=False,
            can_send_audios=False,
            can_send_documents=False,
            can_send_photos=False,
            can_send_videos=False,
            can_send_video_notes=False,
            can_send_voice_notes=False,
            can_send_polls=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False
        )
        await context.bot.set_chat_permissions(chat_id, permissions)
        logger.info(f"Group {chat_id} locked - session remains active")
        
        # Send video with caption
        try:
            await context.bot.send_video(
                chat_id=chat_id,
                video="https://envs.sh/M-d.mp4",
                caption=(
                    "🔒 *Group locked!*\n\n"
                    "No one can send messages.\n"
                    "Session is still active but paused.\n\n"
                    "Use /reopen to unlock the group."
                ),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to send video: {e}")
            # Fallback to text message if video fails
            await update.message.reply_text(
                "🔒 *Group locked!*\n\n"
                "No one can send messages.\n"
                "Session is still active but paused.\n\n"
                "Use /reopen to unlock the group.",
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Failed to lock group {chat_id}: {e}")
        await update.message.reply_text(
            "❌ *Cannot lock group!*\n\n"
            "⚠️ Could not lock the group. Make sure the bot has 'Restrict Members' permission.\n\n"
            "Please grant the permission and try again.",
            parse_mode='Markdown'
        )

async def reopen_session_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unlock the group and continue the session"""
    if update.effective_chat.type == 'private':
        await update.message.reply_text("This command is only available in groups!")
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("❌ This command is only for admins!")
        return
    
    chat_id = update.effective_chat.id
    db = context.bot_data['db']
    
    # Check if there's an active session
    session = await db.get_active_session(chat_id)
    if not session:
        await update.message.reply_text("❌ No active session! Use /start to begin.")
        return
    
    # Unlock the group (session continues)
    try:
        permissions = ChatPermissions(
            can_send_messages=True,
            can_send_audios=True,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=True,
            can_send_voice_notes=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_change_info=False,
            can_invite_users=True,
            can_pin_messages=False
        )
        await context.bot.set_chat_permissions(chat_id, permissions)
        logger.info(f"Group {chat_id} unlocked - session continues")
        
        await update.message.reply_text(
            "🔓 *Group unlocked!*\n\n"
            "✅ Users can now send messages.\n"
            "Session continues - link tracking is active.",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Failed to unlock group {chat_id}: {e}")
        await update.message.reply_text(
            "❌ *Cannot unlock group!*\n\n"
            "⚠️ Could not unlock the group. Make sure the bot has 'Restrict Members' permission.",
            parse_mode='Markdown'
        )

async def end_session_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """End the current group session and clear data"""
    if update.effective_chat.type == 'private':
        await update.message.reply_text("This command is only available in groups!")
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("❌ This command is only for admins!")
        return
    
    chat_id = update.effective_chat.id
    db = context.bot_data['db']
    
    session = await db.get_active_session(chat_id)
    if session:
        session_id = str(session['_id'])
        await db.clear_session_data(chat_id, session_id)
        await db.close_session(chat_id)
        
        # Lock the group so no one can send messages
        try:
            permissions = ChatPermissions(
                can_send_messages=False,
                can_send_audios=False,
                can_send_documents=False,
                can_send_photos=False,
                can_send_videos=False,
                can_send_video_notes=False,
                can_send_voice_notes=False,
                can_send_polls=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False
            )
            await context.bot.set_chat_permissions(chat_id, permissions)
            logger.info(f"Group {chat_id} locked - session ended")
        except Exception as e:
            logger.warning(f"Could not lock group: {e}")
        
        # Send image with caption
        try:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo="https://envs.sh/XD_.jpg",
                caption=(
                    "✅ *Session ended and data cleared!*\n\n"
                    "All tracked links and user data have been removed.\n"
                    "🔒 Group is locked - use /start to unlock and begin a new session."
                ),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to send image: {e}")
            # Fallback to text message if image fails
            await update.message.reply_text(
                "✅ *Session ended and data cleared!*\n\n"
                "All tracked links and user data have been removed.\n"
                "🔒 Group is locked - use /start to unlock and begin a new session.",
                parse_mode='Markdown'
            )
    else:
        await update.message.reply_text("❌ No active session found!")

async def clear_all_messages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete all messages in the group (requires delete permissions)"""
    if update.effective_chat.type == 'private':
        await update.message.reply_text("This command is only available in groups!")
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("❌ This command is only for admins!")
        return
    
    chat_id = update.effective_chat.id
    
    # Send confirmation message
    confirmation_msg = await update.message.reply_text(
        "⚠️ *Warning: Clear All Messages*\n\n"
        "This will attempt to delete all recent messages in this group.\n"
        "Note: Telegram only allows deletion of messages from the last 48 hours.\n\n"
        "⏳ Starting deletion process...",
        parse_mode='Markdown'
    )
    
    deleted_count = 0
    failed_count = 0
    
    try:
        # Get the current message ID
        current_message_id = update.message.message_id
        
        # Try to delete messages going backwards from current message
        # Telegram only allows deletion of messages from last 48 hours
        # We'll try to delete up to 1000 messages (reasonable limit)
        for i in range(current_message_id, max(current_message_id - 1000, 0), -1):
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=i)
                deleted_count += 1
                
                # Update progress every 50 messages
                if deleted_count % 50 == 0:
                    try:
                        await confirmation_msg.edit_text(
                            f"🗑️ *Deleting Messages...*\n\n"
                            f"✅ Deleted: {deleted_count}\n"
                            f"❌ Failed: {failed_count}",
                            parse_mode='Markdown'
                        )
                    except:
                        pass
                        
            except Exception as e:
                failed_count += 1
                # If we get too many failures in a row, stop trying
                if failed_count > 100:
                    break
        
        # Final summary
        await confirmation_msg.edit_text(
            f"✅ *Clear All Complete*\n\n"
            f"🗑️ Deleted: {deleted_count} messages\n"
            f"❌ Failed: {failed_count} messages\n\n"
            f"Note: Only messages from the last 48 hours can be deleted.",
            parse_mode='Markdown'
        )
        logger.info(f"Cleared {deleted_count} messages in chat {chat_id}")
        
    except Exception as e:
        logger.error(f"Error in clearall command: {e}")
        await confirmation_msg.edit_text(
            f"❌ *Error during message deletion*\n\n"
            f"Deleted: {deleted_count}\n"
            f"Failed: {failed_count}\n\n"
            f"Error: {str(e)}",
            parse_mode='Markdown'
        )

async def clear_data_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear bot's tracked messages"""
    if update.effective_chat.type == 'private':
        await update.message.reply_text("This command is only available in groups!")
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("❌ This command is only for admins!")
        return
    
    chat_id = update.effective_chat.id
    db = context.bot_data['db']
    
    session = await db.get_active_session(chat_id)
    if session:
        session_id = str(session['_id'])
        await db.clear_session_data(chat_id, session_id)
        
        await update.message.reply_text(
            "✅ *All tracked data cleared!*\n\n"
            "The session is still active but all previous data has been removed.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ No active session found!")

async def manage_groups_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manage allowed groups (bot owner only)"""
    if update.effective_chat.type != 'private':
        await update.message.reply_text("This command is only available in private chat!")
        return
    
    # Check if user is bot owner
    if update.effective_user.id != config.BOT_OWNER_ID:
        await update.message.reply_text("❌ This command is only for the bot owner!")
        return
    
    keyboard = [
        [InlineKeyboardButton("📋 View Allowed Groups", callback_data='view_groups')],
        [InlineKeyboardButton("➕ Add Group", callback_data='add_group_info')],
        [InlineKeyboardButton("➖ Remove Group", callback_data='remove_group_info')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🛠️ *Group Management Panel*\n\n"
        "Select an option to manage allowed groups:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_group_management_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle group management callbacks"""
    query = update.callback_query
    await query.answer()
    
    db = context.bot_data['db']
    
    if query.data == 'view_groups':
        groups = await db.get_all_allowed_groups()
        
        if not groups:
            await query.edit_message_text(
                "📋 *Allowed Groups*\n\n"
                "No groups have been added yet.",
                parse_mode='Markdown'
            )
        else:
            text = "📋 *Allowed Groups*\n\n"
            for idx, group in enumerate(groups, 1):
                text += f"{idx}. *{group['chat_title']}*\n"
                text += f"   ID: `{group['chat_id']}`\n"
                text += f"   Added: {group['added_at'].strftime('%Y-%m-%d')}\n\n"
            
            await query.edit_message_text(text, parse_mode='Markdown')
    
    elif query.data == 'add_group_info':
        await query.edit_message_text(
            "➕ *Add New Group*\n\n"
            "To add a group:\n"
            "1. Add the bot to your group\n"
            "2. Make the bot an admin\n"
            "3. Note the Group ID shown when you use /start\n"
            "4. Send me: `/addgroup <group_id>`\n\n"
            "Example: `/addgroup -1001234567890`",
            parse_mode='Markdown'
        )
    
    elif query.data == 'remove_group_info':
        await query.edit_message_text(
            "➖ *Remove Group*\n\n"
            "To remove a group:\n"
            "Send me: `/removegroup <group_id>`\n\n"
            "Example: `/removegroup -1001234567890`",
            parse_mode='Markdown'
        )

async def add_group_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a group to allowed list (bot owner only)"""
    if update.effective_user.id != config.BOT_OWNER_ID:
        await update.message.reply_text("❌ This command is only for the bot owner!")
        return
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "❌ Usage: `/addgroup <group_id>`\n"
            "Example: `/addgroup -1001234567890`",
            parse_mode='Markdown'
        )
        return
    
    try:
        chat_id = int(context.args[0])
        db = context.bot_data['db']
        
        # Try to get chat info
        try:
            chat = await context.bot.get_chat(chat_id)
            chat_title = chat.title
        except:
            chat_title = f"Group {chat_id}"
        
        success = await db.add_allowed_group(chat_id, chat_title, update.effective_user.id)
        
        if success:
            await update.message.reply_text(
                f"✅ *Group Added Successfully!*\n\n"
                f"📝 Name: {chat_title}\n"
                f"🆔 ID: `{chat_id}`\n\n"
                f"The group can now use the bot.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Failed to add group!")
    
    except ValueError:
        await update.message.reply_text("❌ Invalid group ID! Must be a number.")
    except Exception as e:
        logger.error(f"Error adding group: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def remove_group_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a group from allowed list (bot owner only)"""
    if update.effective_user.id != config.BOT_OWNER_ID:
        await update.message.reply_text("❌ This command is only for the bot owner!")
        return
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "❌ Usage: `/removegroup <group_id>`\n"
            "Example: `/removegroup -1001234567890`",
            parse_mode='Markdown'
        )
        return
    
    try:
        chat_id = int(context.args[0])
        db = context.bot_data['db']
        
        success = await db.remove_allowed_group(chat_id)
        
        if success:
            await update.message.reply_text(
                f"✅ *Group Removed Successfully!*\n\n"
                f"🆔 ID: `{chat_id}`\n\n"
                f"The group can no longer use the bot.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Group not found in allowed list!")
    
    except ValueError:
        await update.message.reply_text("❌ Invalid group ID! Must be a number.")
    except Exception as e:
        logger.error(f"Error removing group: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

def register_admin_handlers(application):
    """Register all admin command handlers"""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("starts", starts_command))
    application.add_handler(CommandHandler("refresh_admins", refresh_admins_command))
    application.add_handler(CommandHandler("close", close_session_command))
    application.add_handler(CommandHandler("reopen", reopen_session_command))
    application.add_handler(CommandHandler("end", end_session_command))
    application.add_handler(CommandHandler("clear", clear_data_command))
    application.add_handler(CommandHandler("clearall", clear_all_messages_command))
    application.add_handler(CommandHandler("managegroups", manage_groups_command))
    application.add_handler(CommandHandler("addgroup", add_group_command))
    application.add_handler(CommandHandler("removegroup", remove_group_command))
    application.add_handler(CallbackQueryHandler(handle_group_management_callback))