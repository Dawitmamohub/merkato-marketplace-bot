import os
import sys
import logging

# Setup basic logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("🚀 Starting debug bot...")

try:
    # Check environment variables
    from dotenv import load_dotenv
    load_dotenv()
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    print(f"✅ Environment loaded. Token present: {bool(TOKEN)}")
    
    if not TOKEN:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN not found!")
        sys.exit(1)
    
    # Check imports
    print("🔧 Checking imports...")
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Updater, CommandHandler, MessageHandler, Filters,
        CallbackQueryHandler, ConversationHandler, CallbackContext
    )
    print("✅ All imports successful!")
    
    # Test basic bot functionality
    def start(update: Update, context: CallbackContext):
        update.message.reply_text("🤖 Debug Bot is working!")
    
    def main():
        print("🤖 Creating bot instance...")
        updater = Updater(TOKEN, use_context=True)
        dp = updater.dispatcher
        
        print("📝 Adding handlers...")
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("debug", start))
        
        print("🎯 Starting bot polling...")
        updater.start_polling()
        
        print("✅ Debug bot is running successfully!")
        print("💡 Bot should respond to /start and /debug commands")
        print("🛑 Press Ctrl+C to stop")
        
        updater.idle()
    
    if __name__ == '__main__':
        main()
        
except Exception as e:
    print(f"❌ CRITICAL ERROR: {e}")
    print("🔍 Stack trace:")
    import traceback
    traceback.print_exc()
    sys.exit(1)