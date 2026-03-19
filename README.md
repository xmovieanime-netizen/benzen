# Telegram Group Management Bot

A professional Telegram bot designed to manage group interactions, track Twitter/X links with fraud detection, and ensure secure like/engagement sessions with advanced verification features.

## 🌟 Key Features

### Core Functionality
- ✅ **Advanced Link Tracking**: Automatically tracks and encrypts shared Twitter/X links
- 🚨 **Fraud Detection**: Detects duplicate links and multiple submissions in real-time
- 🔒 **Account Protection**: Prevents account flags by managing link sharing
- 👥 **User Verification**: Track and verify user submissions with "ad/done" keyword detection
- 🔇 **Smart Moderation**: Mute/unmute individual users or groups with customizable durations
- 📊 **Session Management**: Complete session lifecycle with close/reopen functionality
- 🗄️ **MongoDB Integration**: Persistent data storage with efficient querying
- 📹 **SR Verification**: Request and track screen recording submissions
- 🔐 **Safe List Management**: Automatic user verification when they send completion messages
- 🎬 **Rich Media Support**: Video and image responses for better user engagement

### Fraud Detection Features
- 🔍 Automatic detection of duplicate link submissions
- ⚠️ Real-time warnings for users submitting multiple links
- 🚨 Fraud alerts when same link is shared by multiple users
- 📈 Comprehensive fraud statistics tracking
- 🗑️ Automatic message deletion for rule violations

### Advanced Moderation
- 🔒 **Group Lock/Unlock**: Close sessions without ending them
- 🔇 **Flexible Muting**: Mute individual users, unsafe users, or all members
- 🔊 **Unmute Options**: Unmute specific users, unsafe users, or everyone
- 🗑️ **Message Management**: Clear bot data or attempt to delete all messages
- 📹 **SR Tracking**: Monitor screen recording request compliance

## 📋 Commands Reference

### General Commands
| Command | Description |
|---------|-------------|
| `/start` | Start the bot (activate in groups, info in private) |
| `/help` | Display complete command menu |
| `/rule` | Show group rules for like sessions |

### Session Management Commands (Admin Only)
| Command | Description |
|---------|-------------|
| `/start` or `/starts` | Activate group session (sends video) |
| `/refresh_admins` | Refresh the admin list for the group |
| `/close` | Lock the group (pause session without ending) |
| `/reopen` | Unlock the group and continue session |
| `/end` | End session and clear all data (sends image) |
| `/clear` | Clear bot's tracked data (keeps session active) |
| `/clearall` | Attempt to delete all recent messages (48h limit) |

### User Tracking Commands
| Command | Description | Admin Required |
|---------|-------------|----------------|
| `/multi` | Show users with multiple links (fraud detection) | No |
| `/list` | Display all users with their submitted links | No |
| `/count` | Show total count of users with submissions | No |
| `/link` | Get all links from a user (reply to message) | No |
| `/srlist` | List users asked for screen recordings | No |

### Verification & Safety Commands
| Command | Description | Admin Required |
|---------|-------------|----------------|
| `/check` | Start tracking "ad"/"done" completion messages | Yes |
| `/safe` | List users who sent ad/done messages (safe list) | Yes |

### Moderation Commands (Admin Only)
| Command | Description |
|---------|-------------|
| `/unsafe` | List unverified users |
| `/muteunsafe [duration]` | Mute all unverified users (default: 3d) |
| `/muteall [duration]` | Alias for `/muteunsafe` |
| `/unmuteunsafe` | Unmute all unverified users |
| `/mute [duration]` | Mute a specific user (reply to message) |
| `/unmute` | Unmute a specific user (reply to message) |
| `/unmuteall` | Unmute all members in the group |
| `/sr` | Request screen recording (reply to message) |
| `/add` | Add user to ad list (reply to message) |

### Bot Owner Commands
| Command | Description |
|---------|-------------|
| `/managegroups` | Manage allowed groups (use in private chat) |
| `/addgroup <chat_id>` | Add a group to allowed list |
| `/removegroup <chat_id>` | Remove a group from allowed list |

## ⏱️ Duration Format

For duration-based commands like `/muteunsafe`, `/muteall`, and `/mute`:

- `2d` - 2 days
- `5h` - 5 hours
- `30m` - 30 minutes
- `2d 5h 30m` - Combined duration

**Default**: 3 days if not specified

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- MongoDB 4.0 or higher (or MongoDB Atlas account)
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- API credentials from [my.telegram.org](https://my.telegram.org)

### Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/AmanBotz/telegram-group-bot.git
cd telegram-group-bot
```

2. **Set up MongoDB**

**Option A - MongoDB Atlas (Cloud - Recommended):**
- Create a free account at [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
- Create a cluster and get your connection string
- Whitelist all IPs (0.0.0.0/0) for Heroku deployment

**Option B - Local MongoDB:**
```bash
# Install MongoDB on your system
# Or use Docker:
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

3. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

Required environment variables:
```env
BOT_TOKEN=your_bot_token_from_botfather
API_ID=your_api_id_from_my_telegram_org
API_HASH=your_api_hash_from_my_telegram_org
MONGODB_URI=your_mongodb_connection_string
BOT_OWNER_ID=your_telegram_user_id
```

4. **Install dependencies**
```bash
pip install -r requirements.txt
```

5. **Run the bot**

**Local Development:**
```bash
python bot.py
```

**Heroku Deployment:**
```bash
# Set USE_WEBHOOK=true in Heroku config vars
# Set WEBHOOK_URL to your Heroku app URL
# Heroku will automatically set PORT
```

## 🏗️ Project Structure

```
telegram-group-bot/
├── bot.py                    # Main entry point with lifecycle hooks
├── config.py                 # Configuration management with validation
├── requirements.txt          # Python dependencies
├── .env.example             # Environment variables template
├── Procfile                 # Heroku deployment configuration
├── database/
│   ├── __init__.py
│   ├── mongodb.py           # MongoDB async operations
│   └── models.py            # Data models (Group, Session, Link, User)
├── handlers/
│   ├── __init__.py
│   ├── admin.py             # Admin commands (start, close, end, etc.)
│   ├── user.py              # User commands (list, count, link, etc.)
│   ├── moderation.py        # Moderation commands (mute, unmute, sr, etc.)
│   └── messages.py          # Message handlers (link tracking, ad detection)
├── utils/
│   ├── __init__.py
│   ├── helpers.py           # Helper functions (encryption, duration parsing)
│   ├── validators.py        # Validation functions
│   └── fraud_detection.py   # Fraud detection logic
└── README.md
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `BOT_TOKEN` | Telegram bot token from BotFather | Yes | - |
| `API_ID` | API ID from my.telegram.org | Yes | - |
| `API_HASH` | API Hash from my.telegram.org | Yes | - |
| `MONGODB_URI` | MongoDB connection string | Yes | - |
| `DATABASE_NAME` | MongoDB database name | No | `group_manager` |
| `BOT_OWNER_ID` | Your Telegram user ID | Yes | - |
| `WEBHOOK_URL` | Webhook URL for Heroku deployment | No* | - |
| `USE_WEBHOOK` | Enable webhook mode (true/false) | No | `false` |
| `PORT` | Port for webhook (auto-set by Heroku) | No | `8443` |
| `ENABLE_FRAUD_DETECTION` | Enable fraud detection | No | `true` |
| `ENABLE_AUTO_WARNINGS` | Enable automatic warnings | No | `true` |
| `MAX_LINKS_PER_USER` | Maximum links per user | No | `1` |
| `DEFAULT_MUTE_DURATION` | Default mute duration (days) | No | `3` |
| `LOG_LEVEL` | Logging level | No | `INFO` |

*Required when `USE_WEBHOOK=true`

### Bot Permissions Required

When adding the bot to your group, ensure it has:
- ✅ Delete messages
- ✅ Restrict members (for muting)
- ✅ Pin messages
- ✅ Manage topics (if applicable)
- ✅ Read message history

## 📖 Usage Guide

### For Bot Owners

1. **Get your Telegram User ID**
   - Message [@userinfobot](https://t.me/userinfobot) on Telegram
   - Add this ID to `BOT_OWNER_ID` in `.env`

2. **Manage allowed groups**
   ```
   # In private chat with bot:
   /managegroups
   
   # After adding bot to a group:
   /addgroup -1001234567890
   ```

### For Group Admins

1. **Start a session**
   ```
   # After bot is added and group is authorized:
   /start
   # Bot sends activation video
   ```

2. **Enable ad/done tracking**
   ```
   /check
   # Bot will now track when users send "ad", "done", "all done", "all dn"
   ```

3. **Monitor submissions**
   ```
   /list          # View all submissions with Twitter and Telegram links
   /safe          # View users who completed (sent ad/done)
   /multi         # Check users with multiple links
   /unsafe        # List unverified users
   /count         # Quick count of submissions
   ```

4. **Moderate users**
   ```
   # Reply to user's message:
   /sr            # Request screen recording
   /link          # View their links
   /mute 2d       # Mute for 2 days
   /unmute        # Unmute user
   
   # Bulk actions:
   /muteunsafe 2d # Mute all unverified users
   /unmuteunsafe  # Unmute all unverified users
   /unmuteall     # Unmute everyone
   ```

5. **Session control**
   ```
   /close         # Lock group (pause submissions)
   /reopen        # Unlock group (resume)
   /end           # End and clear all data
   /clear         # Clear data but keep session active
   ```

## 🛡️ Smart Verification System

### How It Works

1. **User submits Twitter/X link** → Bot tracks silently
2. **Admin runs `/check`** → Bot starts watching for completion messages
3. **User sends "ad" or "done"** → Bot automatically:
   - Adds user to safe list
   - Marks their links as verified
   - Sends confirmation with their Twitter username and link
   - Shows their position number in safe list

### Tracked Keywords
- `ad`
- `done`
- `all done`
- `all dn`

### Safe vs Unsafe Users
- **Safe**: Users who sent completion messages (verified)
- **Unsafe**: Users who submitted links but haven't completed

## 🔒 Fraud Detection

The bot automatically monitors for suspicious behavior:

### Duplicate Link Detection
When multiple users share the same Twitter/X link:

```
🚨 Fraud Alert

Multiple users are sharing the same X account link: username

Suspicious users: user1, user2, user3

⚠️ This behavior is suspicious and will be monitored.
```

### Multiple Submission Prevention
- Bot deletes additional link submissions
- Warns user about violation
- Tracks attempts for admin review

### Encrypted Link Storage
All links are encrypted using SHA-256 (16-char hash) for privacy and security.

## 🔐 Security Features

- **Link Encryption**: SHA-256 hashing for all tracked links
- **Data Persistence**: MongoDB ensures no data loss
- **Admin Authorization**: Sensitive commands require admin permissions
- **Owner Verification**: Group management restricted to bot owner
- **Session Isolation**: Each group session is completely independent
- **Automatic Cleanup**: Session end removes all tracked data

## 🐛 Troubleshooting

### Bot doesn't respond in group
- Ensure the bot is added as admin
- Check if group is in allowed list: `/managegroups` (private chat)
- Verify session is active: `/start`
- Check bot has required permissions

### Commands not working
- Verify bot has admin permissions
- Use `/refresh_admins` to update admin list
- Check logs for error messages
- Ensure you're using commands in group (not private)

### Database connection issues
- Verify MongoDB is running (local) or accessible (Atlas)
- Check `MONGODB_URI` in `.env` or Heroku config vars
- For Atlas: Ensure IP whitelist includes 0.0.0.0/0
- Test connection: MongoDB should log "Connected successfully"

### Links not being tracked
- Ensure session is active (`/start`)
- Check that links are valid Twitter/X URLs
- Verify fraud detection isn't blocking legitimate submissions
- Check if user already submitted max allowed links

### Webhook issues (Heroku)
- Ensure `USE_WEBHOOK=true` in config vars
- Set `WEBHOOK_URL` to your Heroku app URL
- Don't manually set `PORT` (Heroku sets it automatically)
- Check Heroku logs: `heroku logs --tail`

## 📊 Database Collections

The bot uses these MongoDB collections:

- `allowed_groups` - Authorized groups list
- `sessions` - Group session tracking with ad_tracking_enabled flag
- `links` - Link submissions with encryption and verification status
- `safe_list` - Users who sent ad/done messages (verified users)
- `sr_requests` - Screen recording requests
- `ad_list` - Ad list users

## 🚀 Deployment

### Heroku Deployment

1. **Create Heroku app**
```bash
heroku create your-app-name
```

2. **Set config vars**
```bash
heroku config:set BOT_TOKEN=your_token
heroku config:set API_ID=your_api_id
heroku config:set API_HASH=your_api_hash
heroku config:set MONGODB_URI=your_mongodb_uri
heroku config:set BOT_OWNER_ID=your_id
heroku config:set USE_WEBHOOK=true
heroku config:set WEBHOOK_URL=https://your-app-name.herokuapp.com
```

3. **Deploy**
```bash
git push heroku main
```

4. **Check logs**
```bash
heroku logs --tail
```

### Northflank Deployment

Similar to Heroku - set environment variables in the dashboard and deploy from GitHub.

## 🔄 Updates and Maintenance

### Updating the bot
```bash
git pull origin main
pip install -r requirements.txt --upgrade
# Restart the bot or redeploy to Heroku
```

### Database backup
```bash
# Using mongodump
mongodump --uri="your_mongodb_uri" --db=group_manager --out=backup/

# Restore
mongorestore --uri="your_mongodb_uri" --db=group_manager backup/group_manager/
```

## 📝 Development

### Adding new commands

1. Create handler in appropriate file under `handlers/`
2. Register handler in the corresponding `register_*_handlers()` function
3. Update help text in `handlers/user.py`
4. Test in a development group

### Adding new features

1. Update database models in `database/models.py` if needed
2. Add database operations in `database/mongodb.py`
3. Create handler logic in `handlers/`
4. Update configuration in `config.py` if needed
5. Test thoroughly before production deployment

## 📄 License

This project is open source and available under the MIT License.

## 👨‍💻 Author

Created by [@AmanBotz](https://github.com/AmanBotz)

## 🤝 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Contact via Telegram: [@AmanBotz](https://t.me/AmanBotz)

## ⚠️ Disclaimer

This bot is designed for legitimate group management purposes. Users are responsible for ensuring compliance with:
- Telegram's Terms of Service
- Twitter/X's Terms of Service
- Local laws and regulations
- Privacy regulations (GDPR, etc.)

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API wrapper (v20+)
- [MongoDB](https://www.mongodb.com/) - Database solution
- [Motor](https://motor.readthedocs.io/) - Async MongoDB driver for Python

---

**Version**: 2.1.0  
**Last Updated**: November 2025  
**Python**: 3.8+  
**python-telegram-bot**: 20.0+  
**MongoDB**: 4.0+

Made with ❤️ for better Telegram group management
