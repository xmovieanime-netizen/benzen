#!/bin/bash

# Heroku Setup Script
# This script helps update files for Heroku deployment

echo "🚀 Setting up files for Heroku deployment..."
echo ""

# Check if running in the correct directory
if [ ! -f "bot.py" ]; then
    echo "❌ Error: bot.py not found. Please run this script from the project root directory."
    exit 1
fi

# Backup existing files
echo "📦 Creating backups..."
cp bot.py bot.py.backup
cp requirements.txt requirements.txt.backup
cp config.py config.py.backup
echo "✅ Backups created (*.backup files)"
echo ""

# Replace files
echo "🔄 Updating files..."

if [ -f "bot_new.py" ]; then
    cp bot_new.py bot.py
    echo "✅ bot.py updated"
else
    echo "⚠️  bot_new.py not found - skipping"
fi

if [ -f "requirements_new.txt" ]; then
    cp requirements_new.txt requirements.txt
    echo "✅ requirements.txt updated"
else
    echo "⚠️  requirements_new.txt not found - skipping"
fi

echo ""
echo "⚠️  MANUAL ACTION REQUIRED:"
echo ""
echo "Please manually update config.py by adding these lines after BOT_OWNER_ID:"
echo ""
echo "    # Webhook Configuration (for Heroku deployment)"
echo "    WEBHOOK_URL: str = os.getenv('WEBHOOK_URL', '')"
echo "    PORT: int = int(os.getenv('PORT', '8443'))"
echo "    USE_WEBHOOK: bool = os.getenv('USE_WEBHOOK', 'false').lower() == 'true'"
echo ""
echo "And update the validate() method to include:"
echo ""
echo "    if cls.USE_WEBHOOK and not cls.WEBHOOK_URL:"
echo "        raise ValueError('WEBHOOK_URL is required when USE_WEBHOOK is true')"
echo ""
echo "✅ Setup complete! Next steps:"
echo ""
echo "1. Update config.py as shown above"
echo "2. Read QUICK_START.md for deployment instructions"
echo "3. Set up MongoDB Atlas (free tier)"
echo "4. Deploy to Heroku!"
echo ""
echo "📚 Documentation:"
echo "   - QUICK_START.md (fast deployment guide)"
echo "   - HEROKU_DEPLOY.md (detailed instructions)"
echo ""
