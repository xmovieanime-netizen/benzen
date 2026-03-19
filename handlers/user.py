from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
import logging
from utils import is_admin

logger = logging.getLogger(__name__)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = r"""
🤖 *Bot Help Menu*

👤 *General Commands:*
/help — Show this help menu
/rule — Show group rules for sessions

👥 *User Commands:*
/multi — Show users with multiple links
/list — List all users who submitted links
/count — Show total number of users

🛡️ *Admin Commands:*

/start or /starts — Start a new group session
/close — Lock the group (pause session)
/reopen — Unlock the group (continue session)
/end — End session and clear all data
/clear — Clear tracked data (keep session)
/clearall — Delete all messages in group
/unsafe — List unverified users
/safe — List users who sent ad/done
/check — Start tracking ad completion
/muteunsafe \[time\] — Mute unverified users
/unmuteunsafe — Unmute unverified users
/mute \[time\] — Mute specific user (reply)
/unmute — Unmute specific user (reply)
/unmuteall — Unmute all users
/sr — Request screen recording (reply)
/add — Add user to ad list (reply)
/link — Get user's links (reply to user)
/srlist — List SR requests
/refresh\_admins — Refresh admin list

⏱️ *Duration Format:*
Examples: `10s`, `5m`, `2h`, `3d`
Or: `10 seconds`, `5 minutes`, `2 hours`, `3 days`
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def multi_links_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show users with multiple links in current session"""
    if update.effective_chat.type == 'private':
        await update.message.reply_text("This command is only available in groups!")
        return
    
    chat_id = update.effective_chat.id
    db = context.bot_data['db']
    
    session = await db.get_active_session(chat_id)
    if not session:
        await update.message.reply_text("❌ No active session! Use /start to begin.")
        return
    
    session_id = str(session['_id'])
    multi_users = await db.get_users_with_multiple_links(chat_id, session_id)
    
    if not multi_users:
        await update.message.reply_text("✅ No users with multiple links found!")
        return
    
    text = "👥 *Users with Multiple Links:*\n\n"
    for user in multi_users:
        username = user.get('username', 'Unknown')
        count = user.get('count', 0)
        text += f"• @{username} - {count} links\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def list_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all users who submitted links"""
    if update.effective_chat.type == 'private':
        await update.message.reply_text("This command is only available in groups!")
        return
    
    chat_id = update.effective_chat.id
    db = context.bot_data['db']
    
    session = await db.get_active_session(chat_id)
    if not session:
        await update.message.reply_text("❌ No active session! Use /start to begin.")
        return
    
    session_id = str(session['_id'])
    
    # Get all users with their links
    users_with_links = await db.get_all_users_with_links(chat_id, session_id)
    
    if not users_with_links:
        await update.message.reply_text("❌ No users have submitted links yet!")
        return
    
    # Build the list message
    from utils import extract_username_from_link
    
    message = "📋 <b>Users who submitted links:</b>\n\n"
    
    for idx, user_data in enumerate(users_with_links, 1):
        username = user_data.get('username', 'Unknown')
        user_id = user_data.get('user_id')
        links = user_data.get('links', [])
        
        # Get Twitter username from the first link
        twitter_username = extract_username_from_link(links[0]) if links else 'unknown'
        
        # Format: 1. [twitter_username](link) 𝕏 [@telegram_username](tg://user?id=user_id)
        if links:
            twitter_link = links[0]
            message += f"{idx}. <a href='{twitter_link}'>{twitter_username}</a> 𝕏 "
        else:
            message += f"{idx}. {twitter_username} 𝕏 "
        
        # Add Telegram user link
        if username != 'Unknown':
            message += f"<a href='tg://user?id={user_id}'>@{username}</a>\n"
        else:
            message += f"<a href='tg://user?id={user_id}'>User</a>\n"
    
    # Add statistics at the end
    stats = await db.get_session_stats(chat_id, session_id)
    message += f"\n📊 <b>Total:</b> {stats['unique_users']} users | {stats['total_links']} links"
    
    await update.message.reply_text(message, parse_mode='HTML', disable_web_page_preview=True)

async def count_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show total count of users who submitted links"""
    if update.effective_chat.type == 'private':
        await update.message.reply_text("This command is only available in groups!")
        return
    
    chat_id = update.effective_chat.id
    db = context.bot_data['db']
    
    session = await db.get_active_session(chat_id)
    if not session:
        await update.message.reply_text("❌ No active session! Use /start to begin.")
        return
    
    session_id = str(session['_id'])
    stats = await db.get_session_stats(chat_id, session_id)
    
    await update.message.reply_text(
        f"📊 Total users with submitted links: *{stats['unique_users']}*",
        parse_mode='Markdown'
    )

async def get_user_links_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get all links shared by a user (reply to their message)"""
    if update.effective_chat.type == 'private':
        await update.message.reply_text("This command is only available in groups!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Please reply to a user's message to get their links!")
        return
    
    chat_id = update.effective_chat.id
    user_id = update.message.reply_to_message.from_user.id
    username = update.message.reply_to_message.from_user.username or "Unknown"
    db = context.bot_data['db']
    
    session = await db.get_active_session(chat_id)
    if not session:
        await update.message.reply_text("❌ No active session!")
        return
    
    session_id = str(session['_id'])
    links = await db.get_user_links(chat_id, user_id, session_id)
    
    if not links:
        await update.message.reply_text(f"No links found for @{username}")
        return
    
    from utils import encrypt_link
    
    text = f"🔗 *Links from @{username}:*\n\n"
    for idx, link_doc in enumerate(links, 1):
        encrypted = link_doc['encrypted_link']
        text += f"{idx}. 🔐 `{encrypted}`\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def sr_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List users asked to submit screen recordings"""
    if update.effective_chat.type == 'private':
        await update.message.reply_text("This command is only available in groups!")
        return
    
    chat_id = update.effective_chat.id
    db = context.bot_data['db']
    
    sr_list = await db.get_sr_list(chat_id)
    
    if not sr_list:
        await update.message.reply_text("✅ No pending screen recording requests!")
        return
    
    text = "📹 *Users requested to submit SR:*\n\n"
    for user in sr_list:
        username = user.get('username', 'Unknown')
        text += f"• @{username}\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def show_rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show group rules for like sessions"""
    rules_text = """
📜 *Group Rules for Like Sessions*

<blockquote>1️⃣ Submit your Twitter/X link when requested
2️⃣ Complete all required interactions (likes/retweets)
3️⃣ Don't share multiple links unless permitted
4️⃣ Don't share the same link as other users
5️⃣ Verify your submission if asked
6️⃣ Submit screen recording in DM when requested
7️⃣ Follow admin instructions promptly

⚠️ *Violations may result in:*
• Fraud alerts
• Warnings
• Temporary mute
• Removal from session
• Ban from future sessions

🚨 *Fraud Detection Active*
The bot automatically detects:
• Duplicate link submissions
• Multiple accounts sharing same link
• Users submitting excessive links

Stay safe and follow the rules! 🤝

Powered by - @Super_Fasttt_Bot </blockquote>
"""
    await update.message.reply_text(rules_text, parse_mode='Markdown')

def register_user_handlers(application):
    """Register all user command handlers"""
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("multi", multi_links_command))
    application.add_handler(CommandHandler("list", list_users_command))
    application.add_handler(CommandHandler("count", count_users_command))
    application.add_handler(CommandHandler("link", get_user_links_command))
    application.add_handler(CommandHandler("srlist", sr_list_command))
    application.add_handler(CommandHandler("rule", show_rules_command))
