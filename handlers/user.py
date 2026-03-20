from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
import logging
from utils import is_admin, escape_html

logger = logging.getLogger(__name__)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = (
        "🤖 <b>Bot Help Menu</b>\n\n"
        "👤 <b>General Commands:</b>\n"
        "/help — Show this help menu\n"
        "/rule — Show group rules for sessions\n\n"
        "👥 <b>User Commands:</b>\n"
        "/multi — Show users with multiple links\n"
        "/list — List all users who submitted links\n"
        "/count — Show total number of users\n\n"
        "🛡️ <b>Admin Commands:</b>\n\n"
        "/start or /starts — Start a new group session\n"
        "/close — Lock the group (pause session)\n"
        "/reopen — Unlock the group (continue session)\n"
        "/end — End session and clear all data\n"
        "/clear — Clear tracked data (keep session)\n"
        "/clearall — Delete all messages in group\n"
        "/unsafe — List unverified users\n"
        "/safe — List users who sent ad/done\n"
        "/check — Start tracking ad completion\n"
        "/muteunsafe [time] — Mute unverified users\n"
        "/unmuteunsafe — Unmute unverified users\n"
        "/mute [time] — Mute specific user (reply or @username)\n"
        "/unmute — Unmute specific user (reply or @username)\n"
        "/unmuteall — Unmute all users\n"
        "/ban — Ban user from group (reply or @username)\n"
        "/unban — Unban user from group (reply or @username)\n"
        "/sr — Request screen recording (reply)\n"
        "/add — Add user to ad list (reply)\n"
        "/link — Get user's links (reply to user)\n"
        "/srlist — List SR requests\n"
        "/refresh_admins — Refresh admin list\n\n"
        "⏱️ <b>Duration Format:</b>\n"
        "Examples: <code>10s</code>, <code>5m</code>, <code>2h</code>, <code>3d</code>\n"
        "Or: <code>10 seconds</code>, <code>5 minutes</code>, <code>2 hours</code>, <code>3 days</code>"
    )
    await update.message.reply_text(help_text, parse_mode='HTML')


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

    text = "👥 <b>Users with Multiple Links:</b>\n\n"
    for user in multi_users:
        username = escape_html(user.get('username', 'Unknown'))
        count = user.get('count', 0)
        text += f"• @{username} — {count} links\n"

    await update.message.reply_text(text, parse_mode='HTML')


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
    users_with_links = await db.get_all_users_with_links(chat_id, session_id)

    if not users_with_links:
        await update.message.reply_text("❌ No users have submitted links yet!")
        return

    from utils import extract_username_from_link

    message = "📋 <b>Users who submitted links:</b>\n\n"

    for idx, user_data in enumerate(users_with_links, 1):
        username = user_data.get('username', 'Unknown')
        uid = user_data.get('user_id')
        links = user_data.get('links', [])

        twitter_username = extract_username_from_link(links[0]) if links else 'unknown'

        if links:
            twitter_link = links[0]
            message += f"{idx}. <a href='{twitter_link}'>{escape_html(twitter_username)}</a> 𝕏 "
        else:
            message += f"{idx}. {escape_html(twitter_username)} 𝕏 "

        if username != 'Unknown':
            message += f"<a href='tg://user?id={uid}'>@{escape_html(username)}</a>\n"
        else:
            message += f"<a href='tg://user?id={uid}'>User</a>\n"

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
        f"📊 Total users with submitted links: <b>{stats['unique_users']}</b>",
        parse_mode='HTML'
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
        await update.message.reply_text(f"No links found for @{escape_html(username)}")
        return

    text = f"🔗 <b>Links from @{escape_html(username)}:</b>\n\n"
    for idx, link_doc in enumerate(links, 1):
        encrypted = link_doc['encrypted_link']
        text += f"{idx}. 🔐 <code>{encrypted}</code>\n"

    await update.message.reply_text(text, parse_mode='HTML')


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

    text = "📹 <b>Users requested to submit SR:</b>\n\n"
    for user in sr_list:
        username = escape_html(user.get('username', 'Unknown'))
        text += f"• @{username}\n"

    await update.message.reply_text(text, parse_mode='HTML')


async def show_rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show group rules for like sessions"""
    rules_text = (
        "📜 <b>Group Rules for Like Sessions</b>\n\n"
        "<blockquote>"
        "1️⃣ Submit your Twitter/X link when requested\n"
        "2️⃣ Complete all required interactions (likes/retweets)\n"
        "3️⃣ Don't share multiple links unless permitted\n"
        "4️⃣ Don't share the same link as other users\n"
        "5️⃣ Verify your submission if asked\n"
        "6️⃣ Submit screen recording in DM when requested\n"
        "7️⃣ Follow admin instructions promptly\n\n"
        "⚠️ <b>Violations may result in:</b>\n"
        "• Fraud alerts\n"
        "• Warnings\n"
        "• Temporary mute\n"
        "• Removal from session\n"
        "• Ban from future sessions\n\n"
        "🚨 <b>Fraud Detection Active</b>\n"
        "The bot automatically detects:\n"
        "• Duplicate link submissions\n"
        "• Multiple accounts sharing same link\n"
        "• Users submitting excessive links\n\n"
        "Stay safe and follow the rules! 🤝\n\n"
        "Powered by - @Super_Fasttt_Bot"
        "</blockquote>"
    )
    await update.message.reply_text(rules_text, parse_mode='HTML')


def register_user_handlers(application):
    """Register all user command handlers"""
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("multi", multi_links_command))
    application.add_handler(CommandHandler("list", list_users_command))
    application.add_handler(CommandHandler("count", count_users_command))
    application.add_handler(CommandHandler("link", get_user_links_command))
    application.add_handler(CommandHandler("srlist", sr_list_command))
    application.add_handler(CommandHandler("rule", show_rules_command))
