from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes, CommandHandler
from datetime import datetime
import logging
from utils import is_admin, parse_duration, escape_html

logger = logging.getLogger(__name__)

async def unsafe_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List unverified users"""
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
        await update.message.reply_text("❌ No active session!")
        return
    
    session_id = str(session['_id'])
    
    # Get all users with unverified links
    all_links = await db.db.links.find({
        'chat_id': chat_id,
        'session_id': session_id,
        'is_verified': False
    }).to_list(length=None)
    
    if not all_links:
        await update.message.reply_text("✅ All users are verified!")
        return
    
    # Group by user
    unsafe_users = {}
    for link in all_links:
        user_id = link['user_id']
        if user_id not in unsafe_users:
            unsafe_users[user_id] = link['username']
    
    text = "⚠️ Unverified Users:\n\n"
    for idx, username in enumerate(unsafe_users.values(), 1):
        text += f"{idx}. @{username}\n"
    
    # Send as plain text to avoid Markdown parsing errors with special characters in usernames
    await update.message.reply_text(text)

async def mute_unsafe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mute all unverified users"""
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
        await update.message.reply_text("❌ No active session!")
        return
    
    session_id = str(session['_id'])
    duration_str = ' '.join(context.args) if context.args else ''
    duration = parse_duration(duration_str)
    until_date = datetime.now() + duration
    
    # Get unverified users
    all_links = await db.db.links.find({
        'chat_id': chat_id,
        'session_id': session_id,
        'is_verified': False
    }).to_list(length=None)
    
    unique_users = set(link['user_id'] for link in all_links)
    
    muted_count = 0
    failed_count = 0
    
    for user_id in unique_users:
        try:
            await context.bot.restrict_chat_member(
                chat_id,
                user_id,
                permissions={'can_send_messages': False},
                until_date=until_date
            )
            muted_count += 1
        except Exception as e:
            logger.error(f"Failed to mute user {user_id}: {e}")
            failed_count += 1
    
    duration_display = duration_str or '3d'
    await update.message.reply_text(
        f"🔇 <b>Mute Operation Complete</b>\n\n"
        f"✅ Muted: {muted_count} users\n"
        f"❌ Failed: {failed_count} users\n"
        f"⏱️ Duration: {duration_display}",
        parse_mode='HTML'
    )

async def unmute_unsafe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unmute all unverified users"""
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
        await update.message.reply_text("❌ No active session!")
        return
    
    session_id = str(session['_id'])
    
    # Get unverified users
    all_links = await db.db.links.find({
        'chat_id': chat_id,
        'session_id': session_id,
        'is_verified': False
    }).to_list(length=None)
    
    unique_users = set(link['user_id'] for link in all_links)
    
    unmuted_count = 0
    failed_count = 0
    
    for user_id in unique_users:
        try:
            # Restore full permissions
            await context.bot.restrict_chat_member(
                chat_id,
                user_id,
                permissions=ChatPermissions(
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
            )
            unmuted_count += 1
        except Exception as e:
            logger.error(f"Failed to unmute user {user_id}: {e}")
            failed_count += 1
    
    await update.message.reply_text(
        f"🔊 <b>Unmute Operation Complete</b>\n\n"
        f"✅ Unmuted: {unmuted_count} users\n"
        f"❌ Failed: {failed_count} users",
        parse_mode='HTML'
    )

async def request_sr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask user to submit screen recording (reply to their message)"""
    if update.effective_chat.type == 'private':
        await update.message.reply_text("This command is only available in groups!")
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("❌ This command is only for admins!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Please reply to a user's message!")
        return
    
    chat_id = update.effective_chat.id
    user = update.message.reply_to_message.from_user
    db = context.bot_data['db']
    
    username = user.username or user.first_name
    await db.add_to_sr_list(chat_id, user.id, username)
    
    mention = f"@{user.username}" if user.username else user.first_name
    await update.message.reply_text(
        f"📹 {mention}, Please recheck user name your likes are missing and send a screen recording 'DM' Make sure your profile is visible too! with TL profile mentioned or pinned as per post..\n\n"
        f"Contact the admins to submit your SR."
    )

async def add_to_ad_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add user to ad list"""
    if update.effective_chat.type == 'private':
        await update.message.reply_text("This command is only available in groups!")
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("❌ This command is only for admins!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Please reply to a user's message!")
        return
    
    chat_id = update.effective_chat.id
    user = update.message.reply_to_message.from_user
    db = context.bot_data['db']
    
    username = user.username or user.first_name
    await db.add_to_ad_list(chat_id, user.id, username)
    
    mention = f"@{user.username}" if user.username else user.first_name
    await update.message.reply_text(f"✅ {mention} added to ad list!")

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start tracking ad/done messages"""
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
        await update.message.reply_text("❌ No active session! Use /starts to begin.")
        return
    
    session_id = str(session['_id'])
    
    # Enable ad tracking for this session
    await db.enable_ad_tracking(chat_id, session_id)
    
    await update.message.reply_text(
        "✅ Ad tracking has started! I will track 'ad', 'all done', 'all dn', 'done' messages."
    )
    logger.info(f"Ad tracking started in chat {chat_id}, session {session_id}")

async def safe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List users who sent ad/done messages (safe list)"""
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
        await update.message.reply_text("❌ No active session!")
        return
    
    session_id = str(session['_id'])
    
    # Get all users who sent ad messages
    safe_users = await db.get_safe_users(chat_id, session_id)
    
    if not safe_users:
        await update.message.reply_text("❌ No users have sent ad/done messages yet!")
        return
    
    # Build the list message (similar to /list command)
    from utils import extract_username_from_link
    
    message = "✅ <b>Safe List - Users who sent ad/done:</b>\n\n"
    
    for idx, user_data in enumerate(safe_users, 1):
        username = user_data.get('username', 'Unknown')
        user_id = user_data.get('user_id')
        ad_text = user_data.get('ad_text', 'ad')
        
        # Get their twitter link if they submitted one
        user_links = await db.get_user_links(chat_id, user_id, session_id)
        
        if user_links and len(user_links) > 0:
            twitter_username = extract_username_from_link(user_links[0]['link'])
            twitter_link = user_links[0]['link']
            # Use HTML hyperlink for Twitter username
            message += f"{idx}. <a href='{twitter_link}'>{twitter_username}</a> 𝕏 "
        else:
            message += f"{idx}. "
        
        # Add Telegram username with HTML link
        if username != 'Unknown':
            message += f"<a href='tg://user?id={user_id}'>@{username}</a> ✅ {ad_text}\n"
        else:
            message += f"<a href='tg://user?id={user_id}'>User</a> ✅ {ad_text}\n"
    
    # Add statistics at the end
    message += f"\n📊 <b>Total:</b> {len(safe_users)} users marked as safe"
    
    # Send with HTML parse mode for better compatibility
    await update.message.reply_text(message, parse_mode='HTML', disable_web_page_preview=True)

async def mute_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mute a specific user (reply to their message or use username)"""
    if update.effective_chat.type == 'private':
        await update.message.reply_text("This command is only available in groups!")
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("❌ This command is only for admins!")
        return
    
    chat_id = update.effective_chat.id
    user_id = None
    username_display = None
    duration_str = ''
    
    # Check if it's a reply
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        user_id = user.id
        username_display = f"@{user.username}" if user.username else user.first_name
        duration_str = ' '.join(context.args) if context.args else ''
    elif context.args:
        # Try to get username from args
        username_arg = context.args[0].lstrip('@')
        duration_str = ' '.join(context.args[1:]) if len(context.args) > 1 else ''
        
        # First try to find user in database
        db = context.bot_data['db']
        session = await db.get_active_session(chat_id)
        
        user_found = False
        if session:
            session_id = str(session['_id'])
            # Try to find user in links database
            user_link = await db.db.links.find_one({
                'chat_id': chat_id,
                'session_id': session_id,
                'username': username_arg
            })
            
            if user_link:
                user_id = user_link['user_id']
                username_display = f"@{username_arg}"
                user_found = True
        
        # If not found in database, try to find in safe_list
        if not user_found and session:
            safe_user = await db.db.safe_list.find_one({
                'chat_id': chat_id,
                'session_id': session_id,
                'username': username_arg
            })
            
            if safe_user:
                user_id = safe_user['user_id']
                username_display = f"@{username_arg}"
                user_found = True
        
        # If still not found, search all database collections
        if not user_found:
            try:
                user_in_db = await db.db.links.find_one({
                    'username': username_arg
                }) or await db.db.safe_list.find_one({
                    'username': username_arg
                }) or await db.db.ad_list.find_one({
                    'username': username_arg
                })
                
                if user_in_db:
                    user_id = user_in_db['user_id']
                    username_display = f"@{username_arg}"
                    user_found = True
            except Exception as e:
                logger.error(f"Error searching for user in database: {e}")
        
        # If STILL not found, try to get user from group chat members
        if not user_found:
            try:
                # Get all administrators and check their usernames
                chat_members = await context.bot.get_chat_administrators(chat_id)
                for member in chat_members:
                    if member.user.username and member.user.username.lower() == username_arg.lower():
                        user_id = member.user.id
                        username_display = f"@{member.user.username}"
                        user_found = True
                        logger.info(f"Found user {user_id} in chat administrators")
                        break
            except Exception as e:
                logger.error(f"Error fetching chat administrators: {e}")
        
        # Last resort: try using @username mention to get user_id from recent messages
        # This requires the user to have sent at least one message recently
        if not user_found:
            try:
                # Note: Telegram Bot API doesn't provide a direct way to search members by username
                # The user must have interacted with the bot or be in our database
                logger.warning(f"Could not find user @{username_arg} in database or administrators")
            except Exception as e:
                logger.error(f"Error in final user search: {e}")
        
        if not user_found:
            await update.message.reply_text(
                f"❌ User @{username_arg} not found!\n\n"
                "💡 Try one of these methods:\n"
                "• Reply to the user's message with /mute\n"
                "• Make sure the username is correct\n"
                "• User must have sent at least one message in the group"
            )
            return
    else:
        await update.message.reply_text(
            "❌ Usage:\n"
            "• Reply to a user's message: /mute [duration]\n"
            "• Use username: /mute @username [duration]\n\n"
            "Duration examples: 3d, 2h, 30m"
        )
        return
    
    if not user_id:
        await update.message.reply_text("❌ Could not identify user to mute!")
        return
    
    duration = parse_duration(duration_str)
    until_date = datetime.now() + duration
    
    try:
        await context.bot.restrict_chat_member(
            chat_id,
            user_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date
        )
        
        duration_display = duration_str or '3d'
        username_safe = escape_html(username_display)
        
        await update.message.reply_text(
            f"🔇 <b>User Muted</b>\n\n"
            f"👤 User: {username_safe}\n"
            f"⏱️ Duration: {duration_display}",
            parse_mode='HTML'
        )
        logger.info(f"Muted user {user_id} in chat {chat_id} for {duration_display}")
    except Exception as e:
        logger.error(f"Failed to mute user {user_id}: {e}")
        await update.message.reply_text(f"❌ Failed to mute user: {str(e)}")

async def unmute_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unmute a specific user (reply to their message or use username)"""
    if update.effective_chat.type == 'private':
        await update.message.reply_text("This command is only available in groups!")
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("❌ This command is only for admins!")
        return
    
    chat_id = update.effective_chat.id
    user_id = None
    username_display = None
    
    # Check if it's a reply
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        user_id = user.id
        username_display = f"@{user.username}" if user.username else user.first_name
    elif context.args:
        # Try to get username from args
        username_arg = context.args[0].lstrip('@')
        
        # Search for user by username in the database
        db = context.bot_data['db']
        session = await db.get_active_session(chat_id)
        
        user_found = False
        if session:
            session_id = str(session['_id'])
            # Try to find user in links database
            user_link = await db.db.links.find_one({
                'chat_id': chat_id,
                'session_id': session_id,
                'username': username_arg
            })
            
            if user_link:
                user_id = user_link['user_id']
                username_display = f"@{username_arg}"
                user_found = True
        
        # If not found in current session, try to find in safe_list
        if not user_found and session:
            safe_user = await db.db.safe_list.find_one({
                'chat_id': chat_id,
                'session_id': session_id,
                'username': username_arg
            })
            
            if safe_user:
                user_id = safe_user['user_id']
                username_display = f"@{username_arg}"
                user_found = True
        
        # If still not found, search all collections (any session, any chat)
        if not user_found:
            try:
                user_in_db = await db.db.links.find_one({
                    'username': username_arg
                }) or await db.db.safe_list.find_one({
                    'username': username_arg
                }) or await db.db.ad_list.find_one({
                    'username': username_arg
                })
                
                if user_in_db:
                    user_id = user_in_db['user_id']
                    username_display = f"@{username_arg}"
                    user_found = True
            except Exception as e:
                logger.error(f"Error searching for user: {e}")
        
        # If STILL not found, try to get user from group chat members
        if not user_found:
            try:
                # Get all administrators and check their usernames
                chat_members = await context.bot.get_chat_administrators(chat_id)
                for member in chat_members:
                    if member.user.username and member.user.username.lower() == username_arg.lower():
                        user_id = member.user.id
                        username_display = f"@{member.user.username}"
                        user_found = True
                        logger.info(f"Found user {user_id} in chat administrators (unmute)")
                        break
            except Exception as e:
                logger.error(f"Error fetching chat administrators: {e}")
        
        if not user_found:
            await update.message.reply_text(
                f"❌ User @{username_arg} not found!\n\n"
                "💡 Try one of these methods:\n"
                "• Reply to the user's message with /unmute\n"
                "• Make sure the username is correct"
            )
            return
    else:
        await update.message.reply_text(
            "❌ Usage:\n"
            "• Reply to a user's message: /unmute\n"
            "• Use username: /unmute @username"
        )
        return
    
    if not user_id:
        await update.message.reply_text("❌ Could not identify user to unmute!")
        return
    
    try:
        # Restore full permissions for this specific user
        await context.bot.restrict_chat_member(
            chat_id,
            user_id,
            permissions=ChatPermissions(
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
        )
        
        await update.message.reply_text(
            f"🔊 <b>User Unmuted</b>\n\n"
            f"👤 User: {escape_html(username_display)}\n"
            f"✅ All restrictions removed",
            parse_mode='HTML'
        )
        logger.info(f"Unmuted user {user_id} in chat {chat_id}")
    except Exception as e:
        logger.error(f"Failed to unmute user {user_id}: {e}")
        await update.message.reply_text(f"❌ Failed to unmute user: {str(e)}")

async def unmute_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unmute all members in the group"""
    if update.effective_chat.type == 'private':
        await update.message.reply_text("This command is only available in groups!")
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("❌ This command is only for admins!")
        return
    
    chat_id = update.effective_chat.id
    
    try:
        # Get all chat members (this may not work for large groups)
        # Alternative: restore default group permissions
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
        
        await update.message.reply_text(
            "🔊 <b>Unmute All Complete</b>\n\n"
            "✅ All group restrictions have been lifted.\n"
            "📝 Default permissions restored for all members.",
            parse_mode='HTML'
        )
        logger.info(f"All users unmuted in chat {chat_id}")
    except Exception as e:
        logger.error(f"Failed to unmute all users: {e}")
        await update.message.reply_text(
            f"❌ Failed to unmute all users.\n"
            f"Make sure the bot has 'Restrict Members' permission.\n\n"
            f"Error: {str(e)}"
        )

async def ban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban a user from the group (reply to their message or use username)"""
    if update.effective_chat.type == 'private':
        await update.message.reply_text("This command is only available in groups!")
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("❌ This command is only for admins!")
        return
    
    chat_id = update.effective_chat.id
    user_id = None
    username_display = None
    
    # Check if it's a reply
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        user_id = user.id
        username_display = f"@{user.username}" if user.username else user.first_name
    elif context.args:
        # Try to get username from args
        username_arg = context.args[0].lstrip('@')
        
        # Search for user by username in the database
        db = context.bot_data['db']
        session = await db.get_active_session(chat_id)
        
        user_found = False
        if session:
            session_id = str(session['_id'])
            # Try to find user in links database
            user_link = await db.db.links.find_one({
                'chat_id': chat_id,
                'session_id': session_id,
                'username': username_arg
            })
            
            if user_link:
                user_id = user_link['user_id']
                username_display = f"@{username_arg}"
                user_found = True
        
        # If not found in current session, try to find in safe_list
        if not user_found and session:
            safe_user = await db.db.safe_list.find_one({
                'chat_id': chat_id,
                'session_id': session_id,
                'username': username_arg
            })
            
            if safe_user:
                user_id = safe_user['user_id']
                username_display = f"@{username_arg}"
                user_found = True
        
        # If still not found, search all collections (any session, any chat)
        if not user_found:
            try:
                user_in_db = await db.db.links.find_one({
                    'username': username_arg
                }) or await db.db.safe_list.find_one({
                    'username': username_arg
                }) or await db.db.ad_list.find_one({
                    'username': username_arg
                })
                
                if user_in_db:
                    user_id = user_in_db['user_id']
                    username_display = f"@{username_arg}"
                    user_found = True
            except Exception as e:
                logger.error(f"Error searching for user: {e}")
        
        # If STILL not found, try to get user from group chat members
        if not user_found:
            try:
                # Get all administrators and check their usernames
                chat_members = await context.bot.get_chat_administrators(chat_id)
                for member in chat_members:
                    if member.user.username and member.user.username.lower() == username_arg.lower():
                        user_id = member.user.id
                        username_display = f"@{member.user.username}"
                        user_found = True
                        logger.info(f"Found user {user_id} in chat administrators (ban)")
                        break
            except Exception as e:
                logger.error(f"Error fetching chat administrators: {e}")
        
        if not user_found:
            await update.message.reply_text(
                f"❌ User @{username_arg} not found!\n\n"
                "💡 Try one of these methods:\n"
                "• Reply to the user's message with /ban\n"
                "• Make sure the username is correct"
            )
            return
    else:
        await update.message.reply_text(
            "❌ Usage:\n"
            "• Reply to a user's message: /ban\n"
            "• Use username: /ban @username"
        )
        return
    
    if not user_id:
        await update.message.reply_text("❌ Could not identify user to ban!")
        return
    
    try:
        await context.bot.ban_chat_member(chat_id, user_id)
        
        await update.message.reply_text(
            f"🚫 <b>User Banned</b>\n\n"
            f"👤 User: {escape_html(username_display)}\n"
            f"✅ User has been permanently banned from this group.",
            parse_mode='HTML'
        )
        logger.info(f"Banned user {user_id} from chat {chat_id}")
    except Exception as e:
        logger.error(f"Failed to ban user {user_id}: {e}")
        await update.message.reply_text(
            f"❌ Failed to ban user: {str(e)}\n\n"
            "Make sure the bot has 'Ban Users' permission."
        )

async def unban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unban a user from the group (reply to their message or use username)"""
    if update.effective_chat.type == 'private':
        await update.message.reply_text("This command is only available in groups!")
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("❌ This command is only for admins!")
        return
    
    chat_id = update.effective_chat.id
    user_id = None
    username_display = None
    
    # Check if it's a reply
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        user_id = user.id
        username_display = f"@{user.username}" if user.username else user.first_name
    elif context.args:
        # Try to get username from args
        username_arg = context.args[0].lstrip('@')
        
        # Search for user by username in the database
        db = context.bot_data['db']
        session = await db.get_active_session(chat_id)
        
        user_found = False
        if session:
            session_id = str(session['_id'])
            # Try to find user in links database
            user_link = await db.db.links.find_one({
                'chat_id': chat_id,
                'session_id': session_id,
                'username': username_arg
            })
            
            if user_link:
                user_id = user_link['user_id']
                username_display = f"@{username_arg}"
                user_found = True
        
        # If not found in current session, try to find in safe_list
        if not user_found and session:
            safe_user = await db.db.safe_list.find_one({
                'chat_id': chat_id,
                'session_id': session_id,
                'username': username_arg
            })
            
            if safe_user:
                user_id = safe_user['user_id']
                username_display = f"@{username_arg}"
                user_found = True
        
        # If still not found, search all collections (any session, any chat)
        if not user_found:
            try:
                user_in_db = await db.db.links.find_one({
                    'username': username_arg
                }) or await db.db.safe_list.find_one({
                    'username': username_arg
                }) or await db.db.ad_list.find_one({
                    'username': username_arg
                })
                
                if user_in_db:
                    user_id = user_in_db['user_id']
                    username_display = f"@{username_arg}"
                    user_found = True
            except Exception as e:
                logger.error(f"Error searching for user: {e}")
        
        # If STILL not found, try to get user from group chat members
        if not user_found:
            try:
                # Get all administrators and check their usernames
                chat_members = await context.bot.get_chat_administrators(chat_id)
                for member in chat_members:
                    if member.user.username and member.user.username.lower() == username_arg.lower():
                        user_id = member.user.id
                        username_display = f"@{member.user.username}"
                        user_found = True
                        logger.info(f"Found user {user_id} in chat administrators (unban)")
                        break
            except Exception as e:
                logger.error(f"Error fetching chat administrators: {e}")
        
        if not user_found:
            await update.message.reply_text(
                f"❌ User @{username_arg} not found!\n\n"
                "💡 Try one of these methods:\n"
                "• Reply to the user's message with /unban\n"
                "• Make sure the username is correct"
            )
            return
    else:
        await update.message.reply_text(
            "❌ Usage:\n"
            "• Reply to a user's message: /unban\n"
            "• Use username: /unban @username"
        )
        return
    
    if not user_id:
        await update.message.reply_text("❌ Could not identify user to unban!")
        return
    
    try:
        await context.bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
        
        await update.message.reply_text(
            f"✅ <b>User Unbanned</b>\n\n"
            f"👤 User: {escape_html(username_display)}\n"
            f"✅ User can now rejoin the group.",
            parse_mode='HTML'
        )
        logger.info(f"Unbanned user {user_id} from chat {chat_id}")
    except Exception as e:
        logger.error(f"Failed to unban user {user_id}: {e}")
        await update.message.reply_text(
            f"❌ Failed to unban user: {str(e)}\n\n"
            "Make sure the bot has 'Ban Users' permission."
        )

def register_moderation_handlers(application):
    """Register all moderation command handlers"""
    application.add_handler(CommandHandler("unsafe", unsafe_users_command))
    application.add_handler(CommandHandler("muteunsafe", mute_unsafe_command))
    application.add_handler(CommandHandler("muteall", mute_unsafe_command))
    application.add_handler(CommandHandler("unmuteunsafe", unmute_unsafe_command))
    application.add_handler(CommandHandler("mute", mute_user_command))
    application.add_handler(CommandHandler("unmute", unmute_user_command))
    application.add_handler(CommandHandler("unmuteall", unmute_all_command))
    application.add_handler(CommandHandler("ban", ban_user_command))
    application.add_handler(CommandHandler("unban", unban_user_command))
    application.add_handler(CommandHandler("sr", request_sr_command))
    application.add_handler(CommandHandler("add", add_to_ad_command))
    application.add_handler(CommandHandler("check", check_command))
    application.add_handler(CommandHandler("safe", safe_command))