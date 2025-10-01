import os
import json
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, CallbackQueryHandler, ConversationHandler
)

# ✅ Load environment variables for secure deployment
from dotenv import load_dotenv
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),  # Log to console
        logging.FileHandler('bot.log')  # Log to file
    ]
)

# ✅ Get token from environment variable (secure)
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Make sure token exists
if not TOKEN:
    logging.error("❌ No TELEGRAM_BOT_TOKEN found in environment variables!")
    print("❌ Please set TELEGRAM_BOT_TOKEN environment variable")
    exit(1)

# Conversation states
SELECTING_CATEGORY, TYPING_TITLE, TYPING_DESCRIPTION, TYPING_PRICE, TYPING_LOCATION = range(5)

# File paths for data storage
ITEMS_FILE = "marketplace_items.json"
ANALYTICS_FILE = "analytics.json"

# Marketplace categories
CATEGORIES = [
    "📱 Electronics",
    "👕 Clothing",
    "🏠 Home & Garden",
    "🎮 Games & Consoles",
    "📚 Books",
    "🚗 Vehicles",
    "💼 Jobs",
    "🏀 Sports",
    "🎨 Arts & Crafts",
    "🍎 Food & Drinks",
    "🔧 Services",
    "📦 Other"
]

# ✅ ADMIN CONFIGURATION - YOUR USER ID
ADMIN_USER_IDS = [365932771]

# ========== DATA MANAGEMENT FUNCTIONS ==========

def load_items():
    """Load items from JSON file"""
    try:
        with open(ITEMS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_items(items):
    """Save items to JSON file"""
    with open(ITEMS_FILE, 'w') as f:
        json.dump(items, f, indent=2)

def load_analytics():
    """Load analytics data"""
    try:
        with open(ANALYTICS_FILE, 'r') as f:
            data = json.load(f)
            # Convert active_users list back to set
            data['active_users'] = set(data.get('active_users', []))
            return data
    except FileNotFoundError:
        return {'total_users': 0, 'active_users': set(), 'items_listed': 0}

def save_analytics(data):
    """Save analytics data"""
    # Convert set to list for JSON serialization
    data_to_save = data.copy()
    data_to_save['active_users'] = list(data['active_users'])
    with open(ANALYTICS_FILE, 'w') as f:
        json.dump(data_to_save, f, indent=2)

def track_user(user_id, username):
    """Track new users for analytics"""
    analytics = load_analytics()
    user_count_before = len(analytics['active_users'])
    
    if user_id not in analytics['active_users']:
        analytics['active_users'].add(user_id)
        analytics['total_users'] = len(analytics['active_users'])
        save_analytics(analytics)
        logging.info(f"👤 New user: {username} (ID: {user_id})")
        print(f"🎉 New user joined! Total users: {analytics['total_users']}")

def track_item_listed():
    """Track when new items are listed"""
    analytics = load_analytics()
    analytics['items_listed'] = analytics.get('items_listed', 0) + 1
    save_analytics(analytics)
    logging.info(f"📦 New item listed. Total items: {analytics['items_listed']}")

def get_user_items(user_id):
    """Get items posted by a specific user"""
    items = load_items()
    return [item for item in items if item['seller_id'] == user_id]

def get_items_by_category(category):
    """Get items by category"""
    items = load_items()
    return [item for item in items if item['category'] == category and item.get('active', True)]

def get_recent_items(limit=10):
    """Get most recent items"""
    items = load_items()
    # Sort by timestamp (newest first) and return limited number
    items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    return items[:limit]

def is_admin(user_id):
    """Check if user is admin"""
    return user_id in ADMIN_USER_IDS

def count_items_today(items):
    """Count items listed today"""
    today = datetime.now().date()
    count = 0
    for item in items:
        try:
            item_date = datetime.fromisoformat(item['timestamp']).date()
            if item_date == today:
                count += 1
        except:
            continue
    return count

def get_time_ago(timestamp):
    """Convert timestamp to human-readable time ago"""
    try:
        item_time = datetime.fromisoformat(timestamp)
        now = datetime.now()
        diff = now - item_time
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        else:
            return "just now"
    except:
        return "recently"

# ========== BOT COMMAND HANDLERS ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message and main menu"""
    user = update.message.from_user
    
    # Track user for analytics
    track_user(user.id, user.username)
    
    # Load analytics for welcome message
    analytics = load_analytics()
    items_count = len(load_items())
    
    welcome_text = f"""
🏪 **Welcome to Merkato Marketplace, {user.first_name}!** 🏪

📍 *Your community marketplace for buying and selling*

**📊 Marketplace Stats:**
• 👥 {analytics['total_users']} users
• 📦 {items_count} items listed
• 🏷️ {len(CATEGORIES)} categories

**Available Commands:**
/sell - List an item for sale
/buy - Browse items to buy
/myitems - View your listed items
/recent - See recent listings
/help - Get help

**Quick Actions:**
    """
    
    keyboard = [
        [InlineKeyboardButton("🛍️ Browse Items", callback_data="browse")],
        [InlineKeyboardButton("📦 Sell Item", callback_data="sell")],
        [InlineKeyboardButton("🆕 Recent Items", callback_data="recent")],
        [InlineKeyboardButton("📋 My Items", callback_data="my_items"),
         InlineKeyboardButton("❓ Help", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message"""
    help_text = """
🤖 **Merkato Marketplace Commands:**

**Main Commands:**
/sell - List an item for sale
/buy - Browse all items
/myitems - View your listed items
/recent - See recent listings
/help - Show this help message

**How to Use:**
1. Use `/sell` to list items - follow the simple steps
2. Use `/buy` to browse items by category
3. Contact sellers directly via Telegram
4. Manage your items with `/myitems`

**💰 Pricing Tips:**
• Research similar items
• Consider item condition
• Be open to negotiation
• Include delivery options if possible

**🛡️ Safety Tips:**
• Meet in public places
• Inspect items before paying
• Use secure payment methods
• Trust your instincts

*Need help? Just send a message!*
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def recent_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show recent listings"""
    recent_items = get_recent_items(limit=8)
    
    if not recent_items:
        await update.message.reply_text(
            "📭 No items available right now.\n\n"
            "Be the first to list something with /sell !"
        )
        return
    
    text = "🆕 **Recent Listings**\n\n"
    for i, item in enumerate(recent_items, 1):
        time_ago = get_time_ago(item.get('timestamp', ''))
        text += f"{i}. **{item['title']}** - {item['price']} ({time_ago})\n"
        text += f"   📍 {item['location']} | 👤 {item['seller_name']}\n\n"
    
    text += "Use `/buy` to browse by category or `/sell` to list your own item!"
    
    await update.message.reply_text(text, parse_mode='Markdown')

# ========== SELL FLOW ==========

async def sell_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the sell conversation"""
    # Check if this is a callback query or direct message
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        message = query.edit_message_text
    else:
        message = update.message.reply_text
    
    keyboard = []
    for i in range(0, len(CATEGORIES), 2):
        row = []
        if i < len(CATEGORIES):
            row.append(InlineKeyboardButton(CATEGORIES[i], callback_data=f"category_{i}"))
        if i + 1 < len(CATEGORIES):
            row.append(InlineKeyboardButton(CATEGORIES[i+1], callback_data=f"category_{i+1}"))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_sell")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message(
        "📦 **Let's list your item for sale!**\n\n"
        "First, choose a category:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return SELECTING_CATEGORY

async def category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle category selection"""
    query = update.callback_query
    await query.answer()
    
    category_index = int(query.data.split('_')[1])
    context.user_data['category'] = CATEGORIES[category_index]
    
    await query.edit_message_text(
        f"📝 **Category:** {CATEGORIES[category_index]}\n\n"
        "Now, please send me the **title** of your item:\n"
        "(e.g., 'iPhone 13 Pro Max 256GB' or 'Office Desk Chair')"
    )
    
    return TYPING_TITLE

async def title_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive item title"""
    context.user_data['title'] = update.message.text
    
    await update.message.reply_text(
        "📋 Great! Now send me the **description** of your item:\n\n"
        "Include details like:\n"
        "• Condition (new, used, etc.)\n"
        "• Features/specifications\n"
        "• Reason for selling\n"
        "• Any defects or issues"
    )
    
    return TYPING_DESCRIPTION

async def description_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive item description"""
    context.user_data['description'] = update.message.text
    
    await update.message.reply_text(
        "💰 Now send me the **price**:\n\n"
        "Examples:\n"
        "• '15000 ETB'\n"
        "• '100 USD'\n"
        "• '5000 negotiable'\n"
        "• 'Free'\n\n"
        "You can include 'negotiable' if open to offers."
    )
    
    return TYPING_PRICE

async def price_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive item price"""
    context.user_data['price'] = update.message.text
    
    await update.message.reply_text(
        "📍 Finally, send me your **location** or area:\n\n"
        "Examples:\n"
        "• 'Addis Ababa, Bole'\n"
        "• 'Online/Delivery'\n"
        "• 'Meet at City Mall'\n"
        "• 'Specific address (share privately later)'"
    )
    
    return TYPING_LOCATION

async def location_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive location and save the item"""
    context.user_data['location'] = update.message.text
    user = update.message.from_user
    
    # Create item object
    item = {
        'id': len(load_items()) + 1,
        'seller_id': user.id,
        'seller_name': user.first_name,
        'seller_username': user.username,
        'title': context.user_data['title'],
        'description': context.user_data['description'],
        'price': context.user_data['price'],
        'category': context.user_data['category'],
        'location': context.user_data['location'],
        'timestamp': datetime.now().isoformat(),
        'active': True
    }
    
    # Save to storage
    items = load_items()
    items.append(item)
    save_items(items)
    
    # Track for analytics
    track_item_listed()
    
    # Clear user data
    context.user_data.clear()
    
    # Send confirmation
    item_text = f"""
✅ **Item Listed Successfully!**

🏷️ **Title:** {item['title']}
📁 **Category:** {item['category']}
💰 **Price:** {item['price']}
📍 **Location:** {item['location']}
📝 **Description:** {item['description']}

**What's next?**
• Buyers can now find your item with `/buy`
• View your items with `/myitems`
• Be ready to respond to interested buyers!

*Thank you for using Merkato Marketplace! 🏪*
    """
    
    await update.message.reply_text(item_text, parse_mode='Markdown')
    
    return ConversationHandler.END

async def cancel_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the sell conversation"""
    context.user_data.clear()
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("❌ Item listing cancelled.")
    else:
        await update.message.reply_text("❌ Item listing cancelled.")
    
    return ConversationHandler.END

# ========== BUY FLOW ==========

async def browse_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Browse items by category"""
    keyboard = []
    for i in range(0, len(CATEGORIES), 2):
        row = []
        if i < len(CATEGORIES):
            row.append(InlineKeyboardButton(CATEGORIES[i], callback_data=f"browse_{i}"))
        if i + 1 < len(CATEGORIES):
            row.append(InlineKeyboardButton(CATEGORIES[i+1], callback_data=f"browse_{i+1}"))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🆕 Recent Items", callback_data="recent"),
                     InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "🛍️ **Browse Items by Category**\n\nChoose a category to see available items:"
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        query = update.callback_query
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_category_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show items in a specific category"""
    query = update.callback_query
    await query.answer()
    
    category_index = int(query.data.split('_')[1])
    category = CATEGORIES[category_index]
    items = get_items_by_category(category)
    
    if not items:
        await query.edit_message_text(
            f"📭 No items found in **{category}**\n\n"
            "Be the first to list something in this category!\n"
            "Use `/sell` to list your item.",
            parse_mode='Markdown'
        )
        return
    
    # Show first item with navigation
    await show_item_detail(update, context, items, 0, category)

async def show_item_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, items=None, index=0, category=None):
    """Show item details with navigation"""
    if items is None:
        items = load_items()
    
    if not items:
        if update.callback_query:
            await update.callback_query.edit_message_text("📭 No items available right now.")
        else:
            await update.message.reply_text("📭 No items available right now.")
        return
    
    item = items[index]
    
    # Format item text
    time_ago = get_time_ago(item.get('timestamp', ''))
    item_text = f"""
🏷️ **{item['title']}**
💰 **Price:** {item['price']}
📍 **Location:** {item['location']}
📁 **Category:** {item['category']}
🕒 **Listed:** {time_ago}

📝 **Description:**
{item['description']}

👤 **Seller:** {item['seller_name']}
{'@' + item['seller_username'] if item['seller_username'] else 'No username'}
    """
    
    # Create navigation buttons
    keyboard = []
    
    # Contact seller button
    if item['seller_username']:
        contact_button = InlineKeyboardButton(
            "📞 Contact Seller",
            url=f"https://t.me/{item['seller_username']}"
        )
    else:
        contact_button = InlineKeyboardButton("📞 Seller has no username", callback_data="no_username")
    
    keyboard.append([contact_button])
    
    # Navigation buttons
    nav_buttons = []
    if index > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Previous", callback_data=f"nav_{index-1}"))
    
    nav_buttons.append(InlineKeyboardButton(f"{index+1}/{len(items)}", callback_data="count"))
    
    if index < len(items) - 1:
        nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"nav_{index+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Back button
    if category:
        keyboard.append([InlineKeyboardButton("📂 Back to Categories", callback_data="back_to_categories")])
    else:
        keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Store current items and index in context for navigation
    context.user_data['browse_items'] = items
    context.user_data['browse_index'] = index
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            item_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            item_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def navigate_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Navigate between items"""
    query = update.callback_query
    await query.answer()
    
    index = int(query.data.split('_')[1])
    items = context.user_data.get('browse_items', load_items())
    
    await show_item_detail(update, context, items, index)

async def my_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's listed items"""
    user_id = update.message.from_user.id
    items = get_user_items(user_id)
    
    if not items:
        await update.message.reply_text(
            "📭 You haven't listed any items yet.\n\n"
            "Use `/sell` to list your first item and start selling!"
        )
        return
    
    text = "📋 **Your Listed Items**\n\n"
    for i, item in enumerate(items, 1):
        status = "✅ Active" if item['active'] else "❌ Inactive"
        time_ago = get_time_ago(item.get('timestamp', ''))
        text += f"{i}. **{item['title']}** - {item['price']}\n"
        text += f"   📍 {item['location']} | {status} | {time_ago}\n\n"
    
    text += "Use `/sell` to add more items or `/buy` to browse other listings!"
    
    await update.message.reply_text(text, parse_mode='Markdown')

# ========== ADMIN COMMANDS ==========

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin statistics"""
    user_id = update.message.from_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin access required.")
        return
    
    analytics = load_analytics()
    items = load_items()
    total_items = len(items)
    active_items = len([i for i in items if i.get('active', True)])
    today_count = count_items_today(items)
    
    # Calculate items per category
    category_stats = {}
    for item in items:
        cat = item['category']
        category_stats[cat] = category_stats.get(cat, 0) + 1
    
    stats_text = f"""
📊 **Admin Statistics**

👥 **Users:**
• Total Users: {analytics['total_users']}
• Active Users: {len(analytics['active_users'])}

📦 **Items:**
• Total Listed: {total_items}
• Active Items: {active_items}
• Items Today: {today_count}

📈 **Category Distribution:**
"""
    
    for category in CATEGORIES:
        count = category_stats.get(category, 0)
        stats_text += f"• {category}: {count} items\n"
    
    stats_text += f"\n🕒 **Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast message to all users"""
    user_id = update.message.from_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin access required.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📢 **Usage:** /broadcast Your message here\n\n"
            "This will send a message to all bot users."
        )
        return
    
    message = " ".join(context.args)
    analytics = load_analytics()
    
    await update.message.reply_text(
        f"📢 Broadcast prepared for {len(analytics['active_users'])} users:\n\n"
        f"{message}\n\n"
        "⚠️ Note: Full broadcast requires enhanced user tracking."
    )

# ========== BUTTON HANDLERS ==========

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard button presses"""
    query = update.callback_query
    data = query.data
    
    if data == "browse":
        await browse_items(update, context)
    elif data == "sell":
        await sell_start(update, context)
    elif data == "my_items":
        # For callback, we need to send a new message
        user_id = query.from_user.id
        items = get_user_items(user_id)
        
        if not items:
            await query.edit_message_text(
                "📭 You haven't listed any items yet.\n\n"
                "Use /sell to list your first item!"
            )
            return
        
        text = "📋 **Your Listed Items**\n\n"
        for i, item in enumerate(items, 1):
            status = "✅ Active" if item['active'] else "❌ Inactive"
            text += f"{i}. **{item['title']}** - {item['price']} ({status})\n"
        
        text += "\nUse /sell to add more items!"
        
        await query.edit_message_text(text, parse_mode='Markdown')
    elif data == "recent":
        await recent_command(update, context)
    elif data == "help":
        await help_command(update, context)
    elif data == "main_menu":
        await start(update, context)
    elif data == "search":
        await query.edit_message_text("🔍 Search feature coming soon!\n\nUse /buy to browse by category.")
    elif data == "back_to_categories":
        await browse_items(update, context)
    elif data.startswith("category_"):
        await category_selected(update, context)
    elif data.startswith("browse_"):
        await show_category_items(update, context)
    elif data.startswith("nav_"):
        await navigate_items(update, context)
    elif data == "cancel_sell":
        await cancel_sell(update, context)
    elif data == "no_username":
        await query.answer("This seller hasn't set a Telegram username. You can't message them directly.", show_alert=True)
    elif data == "count":
        await query.answer()  # Just acknowledge the button press

# ========== ERROR HANDLING ==========

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors in the bot"""
    logging.error(f"Exception while handling an update: {context.error}")
    
    # Try to notify user about error
    try:
        if update and update.message:
            await update.message.reply_text(
                "❌ Sorry, something went wrong. Please try again or use /help for assistance."
            )
    except:
        pass

# ========== MAIN FUNCTION ==========

def main():
    """Start the bot"""
    print("🚀 Starting Merkato Marketplace Bot...")
    print(f"✅ Token loaded: {TOKEN[:10]}...")  # Only show first 10 chars for security
    print(f"✅ Admin ID: {ADMIN_USER_IDS[0]}")  # Show admin ID for verification
    
    # Load initial analytics
    analytics = load_analytics()
    items = load_items()
    print(f"📊 Loaded: {analytics['total_users']} users, {len(items)} items")
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Sell conversation handler
    sell_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('sell', sell_start),
            CallbackQueryHandler(sell_start, pattern='^sell$')
        ],
        states={
            SELECTING_CATEGORY: [
                CallbackQueryHandler(category_selected, pattern='^category_'),
                CallbackQueryHandler(cancel_sell, pattern='^cancel_sell$')
            ],
            TYPING_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, title_received)],
            TYPING_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description_received)],
            TYPING_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, price_received)],
            TYPING_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, location_received)],
        },
        fallbacks=[
            CommandHandler('cancel', cancel_sell),
            CallbackQueryHandler(cancel_sell, pattern='^cancel_sell$')
        ]
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("buy", browse_items))
    application.add_handler(CommandHandler("myitems", my_items))
    application.add_handler(CommandHandler("recent", recent_command))
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(CommandHandler("broadcast", admin_broadcast))
    application.add_handler(sell_conv_handler)
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    print("✅ Marketplace bot is running!")
    print("📱 Bot is ready to receive messages...")
    print("💡 Press Ctrl+C to stop the bot")
    
    application.run_polling()

if __name__ == '__main__':
    main()