import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8257080955:AAE1FC62_HM3NKYA0QBNbqoAqwzmS0FJZ24"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    await update.message.reply_text(
        f"Hello {user.first_name}! 👋\n"
        f"Welcome to Merkato Sell and Buy Bot!\n\n"
        f"I'm here to help you with buying and selling. "
        f"Send me any message and I'll respond!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🤖 **Merkato Bot Commands:**

/start - Start the bot
/help - Show this help message
/about - About Merkato bot
/sell - List an item for sale
/buy - Browse items for purchase

💬 **Just send me a message to get started!**
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    about_text = """
🏪 **About Merkato Sell & Buy Bot**

This bot helps facilitate buying and selling in your community!

**Features:**
• List items for sale
• Browse available items
• Connect buyers and sellers
• Secure transactions

More features coming soon!
    """
    await update.message.reply_text(about_text, parse_mode='Markdown')

async def sell_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📦 To list an item for sale, please send:\n"
        "• Item name\n• Description\n• Price\n• Photo (if available)\n\n"
        "We'll help you list it!"
    )

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛍️ Browse available items:\n\n"
        "Feature coming soon! Currently working on the item database.\n"
        "For now, you can message sellers directly."
    )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    response = f"✅ Thanks for your message: \"{user_message}\"\n\nI'll help connect you with buyers/sellers soon!"
    await update.message.reply_text(response)

def main():
    print("🚀 Starting Merkato Bot...")
    
    # Create Application
    app = Application.builder().token(TOKEN).build()
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(CommandHandler("sell", sell_command))
    app.add_handler(CommandHandler("buy", buy_command))
    
    # Add message handler for regular messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # Start polling
    print("✅ Bot is running! Press Ctrl+C to stop.")
    print(f"📱 Visit your bot: t.me/Merkato_sell_and_buy_bot")
    app.run_polling()

if __name__ == "__main__":
    main()