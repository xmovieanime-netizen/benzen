from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
import logging
from config import config
from utils import is_admin

logger = logging.getLogger(__name__)

# Full "open" permissions reused in multiple places
_OPEN_PERMS = ChatPermissions(
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

_LOCKED_PERMS = ChatPermissions(
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


async def _unlock_group(context, chat_id: int):
    """Unlock group — swallow permission errors gracefully."""
    try:
        await context.bot.set_chat_permissions(chat_id, _OPEN_PERMS)
        logger.info(f"Group {chat_id} unlocked")
    except Exception as e:
        logger.warning(f"Could not unlock group {chat_id}: {e}")


async def _lock_group(context, chat_id: int):
    """Lock group — swallow permission errors gracefully."""
    try:
        await context.bot.set_chat_permissions(chat_id, _LOCKED_PERMS)
        logger.info(f"Group {chat_id} locked")
    except Exception as e:
        logger.warning(f"Could not lock group {chat_id}: {e}")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    chat_type = update.effective_chat.type
    db = context.bot_data['db']

    if chat_type == 'private':
        await update.message.reply_text(
            "👋 <b>Welcome to Group Management Bot!</b>\n\n"
            "I help manage Telegram groups by:\n"
            "✅ Tracking and encrypting shared Twitter/X links\n"
            "✅ Detecting fraud and duplicate submissions\n"
            "✅ Managing user verification\n"
            "✅ Muting or warning rule-breakers\n\n"
            "Add me to your group and use /help to see all commands!\n\n"
            "🔧 <b>Bot Owner Commands:</b>\n"
            "/managegroups — Configure allowed groups",
            parse_mode='HTML'
        )
        return

    # Group chat
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name

    logger.info(f"Start command in group {chat_id} by user {user_id} ({username})")

    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can activate the bot!")
        return

    if not await db.is_group_allowed(chat_id):
        await update.message.reply_text(
            "⚠️ This group is not authorized!\n\n"
            "Please contact the bot owner to add this group to the allowed list.\n"
            f"Group ID: <code>{chat_id}</code>",
            parse_mode='HTML'
        )
        return

    session = await db.get_active_session(chat_id)

    if not session:
        session_id = await db.create_session(chat_id, user_id)
        if session_id:
            await _unlock_group(context, chat_id)
            try:
                await context.bot.send_video(
                    chat_id=chat_id,
                    video="https://envs.sh/M-h.mp4",
                    caption=(
                        "✅ <b>Group session activated!</b>\n\n"
                        "The bot is now tracking link submissions.\n"
                        "🔓 Group is unlocked — all users can message."
                    ),
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Failed to send start video: {e}")
                await update.message.reply_text(
                    "✅ <b>Group session activated!</b>\n\n"
                    "The bot is now tracking link submissions.\n"
                    "🔓 Group is unlocked — all users can message.",
                    parse_mode='HTML'
                )
        else:
            await update.message.reply_text("❌ Failed to create session!")
    else:
        await _unlock_group(context, chat_id)
        await update.message.reply_text(
            "✅ Session already active!\n"
            "🔓 Group is unlocked — all users can message."
        )


async def starts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Alias for /start"""
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
        await update.message.reply_text(
            f"✅ Admin list refreshed!\n📊 Found <b>{len(admins)}</b> admins.",
            parse_mode='HTML'
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

    session = await db.get_active_session(chat_id)
    if not session:
        await update.message.reply_text("❌ No active session! Use /start to begin.")
        return

    try:
        await _lock_group(context, chat_id)
        try:
            await context.bot.send_video(
                chat_id=chat_id,
                video="https://envs.sh/M-d.mp4",
                caption=(
                    "🔒 <b>Group locked!</b>\n\n"
                    "No one can send messages.\n"
                    "Session is still active but paused.\n\n"
                    "Use /reopen to unlock the group."
                ),
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Failed to send close video: {e}")
            await update.message.reply_text(
                "🔒 <b>Group locked!</b>\n\n"
                "No one can send messages.\n"
                "Session is still active but paused.\n\n"
                "Use /reopen to unlock the group.",
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Failed to lock group {chat_id}: {e}")
        await update.message.reply_text(
            "❌ <b>Cannot lock group!</b>\n\n"
            "⚠️ Make sure the bot has 'Restrict Members' permission.",
            parse_mode='HTML'
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

    session = await db.get_active_session(chat_id)
    if not session:
        await update.message.reply_text("❌ No active session! Use /start to begin.")
        return

    try:
        await _unlock_group(context, chat_id)
        await update.message.reply_text(
            "🔓 <b>Group unlocked!</b>\n\n"
            "✅ Users can now send messages.\n"
            "Session continues — link tracking is active.",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Failed to unlock group {chat_id}: {e}")
        await update.message.reply_text(
            "❌ <b>Cannot unlock group!</b>\n\n"
            "⚠️ Make sure the bot has 'Restrict Members' permission.",
            parse_mode='HTML'
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
    if not session:
        await update.message.reply_text("❌ No active session found!")
        return

    session_id = str(session['_id'])
    await db.clear_session_data(chat_id, session_id)
    await db.close_session(chat_id)
    await _lock_group(context, chat_id)

    try:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo="https://envs.sh/XD_.jpg",
            caption=(
                "✅ <b>Session ended and data cleared!</b>\n\n"
                "All tracked links and user data have been removed.\n"
                "🔒 Group is locked — use /start to unlock and begin a new session."
            ),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Failed to send end photo: {e}")
        await update.message.reply_text(
            "✅ <b>Session ended and data cleared!</b>\n\n"
            "All tracked links and user data have been removed.\n"
            "🔒 Group is locked — use /start to unlock and begin a new session.",
            parse_mode='HTML'
        )


async def clear_all_messages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete recent messages in the group (Telegram allows last 48 hours only)"""
    if update.effective_chat.type == 'private':
        await update.message.reply_text("This command is only available in groups!")
        return

    if not await is_admin(update, context):
        await update.message.reply_text("❌ This command is only for admins!")
        return

    chat_id = update.effective_chat.id

    confirmation_msg = await update.message.reply_text(
        "⚠️ <b>Warning: Clear All Messages</b>\n\n"
        "This will attempt to delete all recent messages in this group.\n"
        "Note: Telegram only allows deletion of messages from the last 48 hours.\n\n"
        "⏳ Starting deletion process...",
        parse_mode='HTML'
    )

    deleted_count = 0
    failed_count = 0

    try:
        current_message_id = update.message.message_id

        for i in range(current_message_id, max(current_message_id - 1000, 0), -1):
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=i)
                deleted_count += 1

                if deleted_count % 50 == 0:
                    try:
                        await confirmation_msg.edit_text(
                            f"🗑️ <b>Deleting Messages...</b>\n\n"
                            f"✅ Deleted: {deleted_count}\n"
                            f"❌ Failed: {failed_count}",
                            parse_mode='HTML'
                        )
                    except Exception:
                        pass

            except Exception:
                failed_count += 1
                if failed_count > 100:
                    break

        await confirmation_msg.edit_text(
            f"✅ <b>Clear All Complete</b>\n\n"
            f"🗑️ Deleted: {deleted_count} messages\n"
            f"❌ Failed/Skipped: {failed_count} messages\n\n"
            f"Note: Only messages from the last 48 hours can be deleted.",
            parse_mode='HTML'
        )
        logger.info(f"Cleared {deleted_count} messages in chat {chat_id}")

    except Exception as e:
        logger.error(f"Error in clearall command: {e}")
        await confirmation_msg.edit_text(
            f"❌ <b>Error during message deletion</b>\n\n"
            f"Deleted: {deleted_count}\n"
            f"Failed: {failed_count}\n\n"
            f"Error: {str(e)}",
            parse_mode='HTML'
        )


async def clear_data_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear bot's tracked data for the current session"""
    if update.effective_chat.type == 'private':
        await update.message.reply_text("This command is only available in groups!")
        return

    if not await is_admin(update, context):
        await update.message.reply_text("❌ This command is only for admins!")
        return

    chat_id = update.effective_chat.id
    db = context.bot_data['db']

    session = await db.get_active_session(chat_id)
    if not session:
        await update.message.reply_text("❌ No active session found!")
        return

    session_id = str(session['_id'])
    await db.clear_session_data(chat_id, session_id)

    await update.message.reply_text(
        "✅ <b>All tracked data cleared!</b>\n\n"
        "The session is still active but all previous data has been removed.",
        parse_mode='HTML'
    )


async def manage_groups_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manage allowed groups (bot owner only)"""
    if update.effective_chat.type != 'private':
        await update.message.reply_text("This command is only available in private chat!")
        return

    if update.effective_user.id != config.BOT_OWNER_ID:
        await update.message.reply_text("❌ This command is only for the bot owner!")
        return

    keyboard = [
        [InlineKeyboardButton("📋 View Allowed Groups", callback_data='view_groups')],
        [InlineKeyboardButton("➕ Add Group", callback_data='add_group_info')],
        [InlineKeyboardButton("➖ Remove Group", callback_data='remove_group_info')]
    ]
    await update.message.reply_text(
        "🛠️ <b>Group Management Panel</b>\n\n"
        "Select an option to manage allowed groups:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
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
                "📋 <b>Allowed Groups</b>\n\nNo groups have been added yet.",
                parse_mode='HTML'
            )
        else:
            text = "📋 <b>Allowed Groups</b>\n\n"
            for idx, group in enumerate(groups, 1):
                text += f"{idx}. <b>{group['chat_title']}</b>\n"
                text += f"   ID: <code>{group['chat_id']}</code>\n"
                text += f"   Added: {group['added_at'].strftime('%Y-%m-%d')}\n\n"
            await query.edit_message_text(text, parse_mode='HTML')

    elif query.data == 'add_group_info':
        await query.edit_message_text(
            "➕ <b>Add New Group</b>\n\n"
            "To add a group:\n"
            "1. Add the bot to your group\n"
            "2. Make the bot an admin\n"
            "3. Note the Group ID shown when you use /start\n"
            "4. Send me: <code>/addgroup &lt;group_id&gt;</code>\n\n"
            "Example: <code>/addgroup -1001234567890</code>",
            parse_mode='HTML'
        )

    elif query.data == 'remove_group_info':
        await query.edit_message_text(
            "➖ <b>Remove Group</b>\n\n"
            "To remove a group:\n"
            "Send me: <code>/removegroup &lt;group_id&gt;</code>\n\n"
            "Example: <code>/removegroup -1001234567890</code>",
            parse_mode='HTML'
        )


async def add_group_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a group to allowed list (bot owner only)"""
    if update.effective_user.id != config.BOT_OWNER_ID:
        await update.message.reply_text("❌ This command is only for the bot owner!")
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Usage: <code>/addgroup &lt;group_id&gt;</code>\n"
            "Example: <code>/addgroup -1001234567890</code>",
            parse_mode='HTML'
        )
        return

    try:
        chat_id = int(context.args[0])
        db = context.bot_data['db']

        try:
            chat = await context.bot.get_chat(chat_id)
            chat_title = chat.title
        except Exception:
            chat_title = f"Group {chat_id}"

        success = await db.add_allowed_group(chat_id, chat_title, update.effective_user.id)

        if success:
            await update.message.reply_text(
                f"✅ <b>Group Added Successfully!</b>\n\n"
                f"📝 Name: {chat_title}\n"
                f"🆔 ID: <code>{chat_id}</code>\n\n"
                f"The group can now use the bot.",
                parse_mode='HTML'
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

    if not context.args:
        await update.message.reply_text(
            "❌ Usage: <code>/removegroup &lt;group_id&gt;</code>\n"
            "Example: <code>/removegroup -1001234567890</code>",
            parse_mode='HTML'
        )
        return

    try:
        chat_id = int(context.args[0])
        db = context.bot_data['db']

        success = await db.remove_allowed_group(chat_id)

        if success:
            await update.message.reply_text(
                f"✅ <b>Group Removed Successfully!</b>\n\n"
                f"🆔 ID: <code>{chat_id}</code>\n\n"
                f"The group can no longer use the bot.",
                parse_mode='HTML'
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
    # Pattern-filtered callback handler — only handles known group-management callbacks
    application.add_handler(
        CallbackQueryHandler(
            handle_group_management_callback,
            pattern=r'^(view_groups|add_group_info|remove_group_info)$'
        )
    )
