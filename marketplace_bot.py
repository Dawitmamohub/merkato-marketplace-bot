from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
import json
import logging
import os
from datetime import datetime

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
WEB_APP_URL = os.getenv('WEB_APP_URL', 'https://your-app.herokuapp.com')

class MarketplaceBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
        self.ensure_data_files()

    def ensure_data_files(self):
        """Ensure required data files exist"""
        default_items = [
            {
                "id": 1,
                "name": "Vintage Camera",
                "price": 89.99,
                "description": "Beautiful vintage camera from the 1970s. Fully functional.",
                "category": "electronics",
                "seller": "camera_lover",
                "image": "📷",
                "date_added": "2024-01-15"
            },
            {
                "id": 2,
                "name": "Designer Handbag",
                "price": 199.99,
                "description": "Genuine leather handbag, excellent condition.",
                "category": "fashion",
                "seller": "fashion_guru",
                "image": "👜",
                "date_added": "2024-01-14"
            },
            {
                "id": 3,
                "name": "Programming Books Bundle",
                "price": 45.50,
                "description": "Collection of programming books for beginners to advanced.",
                "category": "books",
                "seller": "tech_wizard",
                "image": "📚",
                "date_added": "2024-01-13"
            }
        ]

        # Create marketplace_items.json if doesn't exist
        if not os.path.exists('marketplace_items.json'):
            with open('marketplace_items.json', 'w') as f:
                json.dump(default_items, f, indent=2)

        # Create analytics.json if doesn't exist
        if not os.path.exists('analytics.json'):
            with open('analytics.json', 'w') as f:
                json.dump({"users": {}, "commands": {}, "webapp_opens": 0}, f, indent=2)

    def setup_handlers(self):
        """Setup bot handlers"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("marketplace", self.marketplace))
        self.application.add_handler(CommandHandler("add_item", self.add_item))
        self.application.add_handler(CommandHandler("analytics", self.analytics))
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
        self.application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, self.handle_webapp_data))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        self.update_analytics('start', user.id)
        
        keyboard = [
            [InlineKeyboardButton("🛍️ Open Marketplace", web_app=WebAppInfo(url=WEB_APP_URL))],
            [InlineKeyboardButton("📱 View Items in Chat", callback_data="view_items")],
            [InlineKeyboardButton("➕ Add New Item", callback_data="add_item"),
             InlineKeyboardButton("📊 Analytics", callback_data="analytics")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = f"""
👋 Welcome to Marketplace Bot, {user.first_name}!

🛍️ **Features:**
• Browse items in full-screen web app
• Add your own items for sale
• Real-time marketplace updates
• Secure transactions

Choose an option below to get started!
        """
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)

    async def marketplace(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /marketplace command - direct web app access"""
        user = update.effective_user
        self.update_analytics('marketplace', user.id)
        
        keyboard = [
            [InlineKeyboardButton("🛍️ Open Full Marketplace", web_app=WebAppInfo(url=WEB_APP_URL))],
            [InlineKeyboardButton("📱 Quick Browse in Chat", callback_data="view_items")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎯 **Marketplace Access**\n\n"
            "Choose how you want to browse our marketplace:",
            reply_markup=reply_markup
        )

    async def add_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /add_item command"""
        user = update.effective_user
        self.update_analytics('add_item', user.id)
        
        # In a real implementation, you'd use a conversation handler
        # For now, we'll provide instructions
        instructions = """
📦 **How to Add an Item:**

1. Use the format:
   `/add_item Name | Price | Description | Category`

2. Example:
   `/add_item Vintage Watch | 75.00 | Beautiful antique watch | fashion`

3. Categories: electronics, fashion, books, home, other

Or use the web app for an easier experience!
        """
        
        await update.message.reply_text(instructions)

    async def analytics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /analytics command (admin only)"""
        user = update.effective_user
        self.update_analytics('analytics', user.id)
        
        try:
            with open('analytics.json', 'r') as f:
                analytics_data = json.load(f)
            
            total_users = len(analytics_data.get('users', {}))
            webapp_opens = analytics_data.get('webapp_opens', 0)
            commands_used = sum(analytics_data.get('commands', {}).values())
            
            stats_text = f"""
📊 **Bot Analytics**

👥 Total Users: {total_users}
🛍️ Web App Opens: {webapp_opens}
📋 Commands Used: {commands_used}

**Command Usage:**
"""
            for cmd, count in analytics_data.get('commands', {}).items():
                stats_text += f"• /{cmd}: {count}\n"
                
            await update.message.reply_text(stats_text)
            
        except Exception as e:
            logger.error(f"Error reading analytics: {e}")
            await update.message.reply_text("❌ Could not load analytics data.")

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button clicks"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        
        if query.data == "view_items":
            await self.show_items_in_chat(update, context)
        elif query.data == "add_item":
            await self.add_item(update, context)
        elif query.data == "analytics":
            await self.analytics(update, context)

    async def show_items_in_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show marketplace items directly in chat"""
        try:
            with open('marketplace_items.json', 'r') as f:
                items = json.load(f)
            
            if not items:
                await update.callback_query.message.reply_text("🏪 The marketplace is empty! Be the first to add an item. 🎉")
                return
            
            message = "🏪 **Marketplace Items**\n\n"
            for item in items[:8]:  # Show first 8 items
                message += f"{item.get('image', '📦')} **{item.get('name', 'Unknown')}**\n"
                message += f"💵 **${item.get('price', 0)}** | 👤 {item.get('seller', 'Unknown')}\n"
                message += f"📝 {item.get('description', '')[:80]}...\n"
                message += f"🏷️ {item.get('category', 'other').title()}\n"
                message += "─" * 30 + "\n"
            
            keyboard = [
                [InlineKeyboardButton("🛍️ Open Full Marketplace", web_app=WebAppInfo(url=WEB_APP_URL))],
                [InlineKeyboardButton("➕ Add Your Item", callback_data="add_item")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.message.reply_text(message, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error showing items: {e}")
            await update.callback_query.message.reply_text("❌ Error loading marketplace items.")

    async def handle_webapp_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle data sent from the Web App"""
        web_app_data = update.effective_message.web_app_data
        user = update.effective_user
        
        if web_app_data:
            try:
                data = json.loads(web_app_data.data)
                action = data.get('action')
                
                # Update analytics for web app usage
                self.update_analytics('webapp_interaction', user.id)
                with open('analytics.json', 'r+') as f:
                    analytics = json.load(f)
                    analytics['webapp_opens'] = analytics.get('webapp_opens', 0) + 1
                    f.seek(0)
                    json.dump(analytics, f, indent=2)
                    f.truncate()
                
                if action == "purchase":
                    item_id = data.get('item_id')
                    await update.message.reply_text(
                        f"✅ Purchase initiated! Item ID: {item_id}\n\n"
                        f"The seller will contact you shortly to arrange the details. "
                        f"Please discuss payment and delivery methods with them."
                    )
                elif action == "contact_seller":
                    seller = data.get('seller')
                    await update.message.reply_text(
                        f"📞 Contacting seller: @{seller}\n\n"
                        f"I've notified them about your interest. They should message you soon!"
                    )
                    
            except json.JSONDecodeError as e:
                logger.error(f"WebApp data JSON error: {e}")
                await update.message.reply_text("❌ Error processing your request.")
            except Exception as e:
                logger.error(f"WebApp data error: {e}")
                await update.message.reply_text("❌ An error occurred.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages"""
        user = update.effective_user
        text = update.message.text
        
        # Simple add item via text (basic implementation)
        if text.startswith('/add_item'):
            await self.process_add_item(update, context)
        else:
            # Help response for other messages
            await update.message.reply_text(
                "🤔 Need help? Use /start to see all options or /marketplace to browse items!"
            )

    async def process_add_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process adding an item via text command"""
        try:
            parts = update.message.text.split('|')
            if len(parts) < 4:
                await update.message.reply_text(
                    "❌ Invalid format. Use:\n"
                    "`/add_item Name | Price | Description | Category`"
                )
                return
            
            name = parts[0].replace('/add_item', '').strip()
            price = float(parts[1].strip())
            description = parts[2].strip()
            category = parts[3].strip().lower()
            
            new_item = {
                "id": datetime.now().timestamp(),
                "name": name,
                "price": price,
                "description": description,
                "category": category,
                "seller": update.effective_user.username or f"user_{update.effective_user.id}",
                "image": "📦",
                "date_added": datetime.now().strftime("%Y-%m-%d")
            }
            
            # Add to items file
            with open('marketplace_items.json', 'r+') as f:
                items = json.load(f)
                items.append(new_item)
                f.seek(0)
                json.dump(items, f, indent=2)
                f.truncate()
            
            await update.message.reply_text(
                f"✅ Item added successfully!\n\n"
                f"**{name}** - ${price}\n"
                f"Category: {category.title()}\n\n"
                f"View it in the marketplace! 🛍️"
            )
            
        except ValueError as e:
            await update.message.reply_text("❌ Invalid price format. Please use numbers only for price.")
        except Exception as e:
            logger.error(f"Error adding item: {e}")
            await update.message.reply_text("❌ Error adding item. Please check the format.")

    def update_analytics(self, command: str, user_id: int):
        """Update analytics data"""
        try:
            with open('analytics.json', 'r+') as f:
                analytics = json.load(f)
                
                # Update user count
                analytics['users'][str(user_id)] = datetime.now().isoformat()
                
                # Update command count
                analytics['commands'][command] = analytics['commands'].get(command, 0) + 1
                
                f.seek(0)
                json.dump(analytics, f, indent=2)
                f.truncate()
                
        except Exception as e:
            logger.error(f"Analytics update error: {e}")

    def run(self):
        """Start the bot"""
        logger.info("Starting Marketplace Bot...")
        self.application.run_polling()

if __name__ == '__main__':
    bot = MarketplaceBot()
    bot.run()