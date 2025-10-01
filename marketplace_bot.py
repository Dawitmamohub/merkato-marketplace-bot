import os
import json
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, CallbackQueryHandler, ConversationHandler
)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    logging.error("❌ No TELEGRAM_BOT_TOKEN found!")
    exit(1)

# Conversation states
SELECTING_CATEGORY, TYPING_TITLE, TYPING_DESCRIPTION, TYPING_PRICE, TYPING_LOCATION = range(5)

# File paths
ITEMS_FILE = "marketplace_items.json"
ANALYTICS_FILE = "analytics.json"

# Marketplace categories
CATEGORIES = [
    "📱 Electronics", "👕 Clothing", "🏠 Home & Garden", "🎮 Games & Consoles",
    "📚 Books", "🚗 Vehicles", "💼 Jobs", "🏀 Sports", 
    "🎨 Arts & Crafts", "🍎 Food & Drinks", "🔧 Services", "📦 Other"
]

ADMIN_USER_IDS = [365932771]

# ========== BUTTON LAYOUTS ==========

def main_menu_buttons():
    """Main menu buttons"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍️ Browse Items", callback_data="main_browse")],
        [InlineKeyboardButton("📦 Sell Item", callback_data="main_sell")],
        [InlineKeyboardButton("📋 My Items", callback_data="main_myitems")],
        [InlineKeyboardButton("🆕 Recent Listings", callback_data="main_recent"),
         InlineKeyboardButton("❓ Help", callback_data="main_help")]
    ])

def category_buttons(action_prefix="category"):
    """Category selection buttons"""
    keyboard = []
    for i in range(0, len(CATEGORIES), 3):
        row = []
        for j in range(3):
            if i + j < len(CATEGORIES):
                row.append(InlineKeyboardButton(
                    CATEGORIES[i + j], 
                    callback_data=f"{action_prefix}_{i + j}"
                ))
        if row:
            keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def browse_navigation_buttons(items, current_index, category_index=None):
    """Navigation buttons for browsing items"""
    buttons = []
    
    # Contact Seller Button
    if items and current_index < len(items):
        item = items[current_index]
        if item.get('seller_username'):
            buttons.append([InlineKeyboardButton(
                "📞 Contact Seller", 
                url=f"https://t.me/{item['seller_username']}"
            )])
        else:
            buttons.append([InlineKeyboardButton(
                "📞 Seller (No Username)", 
                callback_data="no_username"
            )])
    
    # Navigation Buttons
    nav_buttons = []
    if current_index > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Previous", callback_data=f"nav_{current_index-1}"))
    
    nav_buttons.append(InlineKeyboardButton(f"{current_index+1}/{len(items)}", callback_data="page_info"))
    
    if current_index < len(items) - 1:
        nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"nav_{current_index+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # Action Buttons
    action_buttons = []
    if category_index is not None:
        action_buttons.append(InlineKeyboardButton("📂 Back to Categories", callback_data="back_categories"))
    action_buttons.append(InlineKeyboardButton("🛍️ Browse More", callback_data="main_browse"))
    action_buttons.append(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
    
    buttons.append(action_buttons)
    
    return InlineKeyboardMarkup(buttons)

def sell_flow_buttons():
    """Buttons for sell flow"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚫 Cancel Listing", callback_data="cancel_sell")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
    ])

def quick_action_buttons():
    """Quick action buttons for various screens"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍️ Browse", callback_data="main_browse"),
         InlineKeyboardButton("📦 Sell", callback_data="main_sell")],
        [InlineKeyboardButton("📋 My Items", callback_data="main_myitems"),
         InlineKeyboardButton("🆕 Recent", callback_data="main_recent")],
        [InlineKeyboardButton("❓ Help", callback_data="main_help")]
    ])

# ========== DATA MANAGEMENT ==========

def load_items():
    try:
        with open(ITEMS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_items(items):
    try:
        with open(ITEMS_FILE, 'w') as f:
            json.dump(items, f, indent=2)
    except Exception as e:
        logging.error(f"Error saving items: {e}")

def load_analytics():
    try:
        with open(ANALYTICS_FILE, 'r') as f:
            data = json.load(f)
            data['active_users'] = set(data.get('active_users', []))
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {'total_users': 0, 'active_users': set(), 'items_listed': 0}

def save_analytics(data):
    try:
        data_to_save = data.copy()
        data_to_save['active_users'] = list(data['active_users'])
        with open(ANALYTICS_FILE, 'w') as f:
            json.dump(data_to_save, f, indent=2)
    except Exception as e:
        logging.error(f"Error saving analytics: {e}")

def track_user(user_id, username):
    try:
        analytics = load_analytics()
        if user_id not in analytics['active_users']:
            analytics['active_users'].add(user_id)
            analytics['total_users'] = len(analytics['active_users'])
            save_analytics(analytics)
            print(f"🎉 New user: {username} - Total: {analytics['total_users']}")
    except Exception as e:
        print(f"Error tracking user: {e}")

def track_item_listed():
    try:
        analytics = load_analytics()
        analytics['items_listed'] = analytics.get('items_listed', 0) + 1
        save_analytics(analytics)
        print(f"📦 New item listed. Total: {analytics['items_listed']}")
    except Exception as e:
        print(f"Error tracking item: {e}")

def get_user_items(user_id):
    items = load_items()
    return [item for item in items if item.get('seller_id') == user_id]

def get_items_by_category(category):
    items = load_items()
    return [item for item in items if item.get('category') == category and item.get('active', True)]

def get_recent_items(limit=10):
    items = load_items()
    items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    return items[:limit]

def is_admin(user_id):
    return user_id in ADMIN_USER_IDS

def get_time_ago(timestamp):
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

# ========== BOT COMMANDS WITH BUTTONS ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command with main menu buttons and persistent keyboard button"""
    try:
        user = update.message.from_user
        track_user(user.id, user.username)
        
        analytics = load_analytics()
        items_count = len(load_items())
        
        welcome_text = f"""
🏪 **Welcome to Merkato Marketplace, {user.first_name}!** 

🤖 *Your community marketplace for buying and selling*

📊 **Marketplace Stats:**
• 👥 {analytics['total_users']} users
• 📦 {items_count} items listed
• 🏷️ {len(CATEGORIES)} categories

💡 **Choose an action below or use commands:**
`/sell` - List item | `/buy` - Browse | `/myitems` - Your items
        """
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=main_menu_buttons(),
            parse_mode='Markdown'
        )
        
        # Add persistent keyboard button at bottom
        persistent_keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton("Marketplace")]],
            resize_keyboard=True,
            one_time_keyboard=False
        )
        await update.message.reply_text(
            "Use the button below for quick access:",
            reply_markup=persistent_keyboard
        )
    except Exception as e:
        print(f"Error in start: {e}")
        await update.message.reply_text(
            "❌ Error loading bot. Please try again.",
            reply_markup=quick_action_buttons()
        )

# ========== HANDLER FOR MARKETPLACE BUTTON ==========

async def marketplace_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the 'Marketplace' button to show selling items"""
    try:
        user = update.message.from_user
        items = get_user_items(user.id)
        
        if not items:
            text = "📭 **You haven't listed any items yet!**\n\nStart selling and make your first listing! 🎉"
            await update.message.reply_text(text, reply_markup=main_menu_buttons())
            return
        
        text = f"📋 **Your Listed Items** ({len(items)} total)\n\n"
        for i, item in enumerate(items, 1):
            time_ago = get_time_ago(item.get('timestamp', ''))
            text += f"**{i}. {item['title']}**\n"
            text += f"   💰 {item['price']} | 📍 {item['location']}\n"
            text += f"   🏷️ {item['category']} | 🕒 {time_ago}\n\n"
        
        await update.message.reply_text(text, reply_markup=main_menu_buttons())
    except Exception as e:
        print(f"Error in marketplace_button_handler: {e}")
        await update.message.reply_text("❌ Error loading your items.", reply_markup=main_menu_buttons())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command with quick actions"""
    help_text = """
🤖 **Merkato Marketplace - Complete Guide**

🛍️ **BUYING:**
• Browse items by category
• Contact sellers directly
• Negotiate prices
• Meet safely

📦 **SELLING:**
• List items in 5 easy steps
• Set your price
• Describe item condition
• Choose pickup location

⚡ **QUICK COMMANDS:**
`/start` - Main menu
`/sell` - List item for sale  
`/buy` - Browse items
`/myitems` - Your listings
`/recent` - Newest items
`/help` - This message

🛡️ **SAFETY TIPS:**
• Meet in public places
• Inspect before buying
• Use secure payments
• Trust your instincts
    """
    
    if update.message:
        await update.message.reply_text(help_text, parse_mode='Markdown', reply_markup=quick_action_buttons())
    else:
        query = update.callback_query
        await query.edit_message_text(help_text, parse_mode='Markdown', reply_markup=quick_action_buttons())

async def recent_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recent listings with browse buttons"""
    try:
        recent_items = get_recent_items(limit=6)
        
        if not recent_items:
            text = "📭 **No items available yet!**\n\nBe the first to list something! 🎉"
            await show_message(update, text, main_menu_buttons())
            return
        
        text = "🆕 **Recent Listings**\n\n"
        for i, item in enumerate(recent_items, 1):
            time_ago = get_time_ago(item.get('timestamp', ''))
            text += f"**{i}. {item['title']}**\n"
            text += f"   💰 {item['price']} | 📍 {item['location']}\n"
            text += f"   👤 {item['seller_name']} | 🕒 {time_ago}\n\n"
        
        text += "💡 *Browse categories to see all available items*"
        
        await show_message(update, text, InlineKeyboardMarkup([
            [InlineKeyboardButton("🛍️ Browse All Categories", callback_data="main_browse")],
            [InlineKeyboardButton("📦 List Your Item", callback_data="main_sell")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]))
    except Exception as e:
        print(f"Error in recent: {e}")
        await show_message(update, "❌ Error loading recent items.", quick_action_buttons())

# ========== BUY FLOW WITH BUTTONS ==========

async def browse_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Browse categories with buttons"""
    text = "🛍️ **Browse Marketplace**\n\nChoose a category to explore items:"
    await show_message(update, text, category_buttons("browse"))

async def show_category_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show items in selected category"""
    try:
        query = update.callback_query
        await query.answer()
        
        category_index = int(query.data.split('_')[1])
        category = CATEGORIES[category_index]
        items = get_items_by_category(category)
        
        if not items:
            text = f"📭 **No items in {category}**\n\nBe the first to list something in this category! 🎉"
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📦 List Item Here", callback_data="main_sell")],
                    [InlineKeyboardButton("📂 Other Categories", callback_data="main_browse")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
                ]),
                parse_mode='Markdown'
            )
            return
        
        # Store category context for navigation
        context.user_data['current_category'] = category_index
        await show_item_detail(update, context, items, 0)
        
    except Exception as e:
        print(f"Error in show_category_items: {e}")
        await show_message(update, "❌ Error loading category.", main_menu_buttons())

async def show_item_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, items=None, index=0):
    """Show item details with navigation buttons"""
    try:
        if items is None:
            items = load_items()
        
        if not items:
            await show_message(update, "📭 No items available.", main_menu_buttons())
            return
        
        item = items[index]
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
{('@' + item['seller_username']) if item['seller_username'] else '📞 (No username - cannot contact directly)'}
        """
        
        # Get category context for back button
        category_index = context.user_data.get('current_category')
        
        await show_message(
            update, 
            item_text, 
            browse_navigation_buttons(items, index, category_index)
        )
        
        # Store for navigation
        context.user_data['browse_items'] = items
        context.user_data['browse_index'] = index
        
    except Exception as e:
        print(f"Error in show_item_detail: {e}")
        await show_message(update, "❌ Error loading item.", main_menu_buttons())

async def navigate_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Navigate between items using buttons"""
    try:
        query = update.callback_query
        await query.answer()
        
        index = int(query.data.split('_')[1])
        items = context.user_data.get('browse_items', load_items())
        
        if 0 <= index < len(items):
            await show_item_detail(update, context, items, index)
        else:
            await query.answer("❌ No more items in this direction", show_alert=True)
            
    except Exception as e:
        print(f"Error in navigate_items: {e}")
        await query.answer("❌ Navigation error", show_alert=True)

# ========== SELL FLOW WITH BUTTONS ==========

async def start_sell_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start selling with category buttons"""
    text = "📦 **List Item for Sale**\n\nFirst, choose a category for your item:"
    await show_message(update, text, category_buttons("sell_category"))

async def sell_category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle category selection for selling"""
    try:
        query = update.callback_query
        await query.answer()
        
        category_index = int(query.data.split('_')[1])
        context.user_data['sell_category'] = CATEGORIES[category_index]
        
        await query.edit_message_text(
            f"📝 **Category:** {CATEGORIES[category_index]}\n\n"
            "Now send me the **title** of your item:\n"
            "*Example: 'iPhone 13 Pro Max 256GB'*",
            parse_mode='Markdown',
            reply_markup=sell_flow_buttons()
        )
        
        return TYPING_TITLE
    except Exception as e:
        print(f"Error in sell_category_selected: {e}")
        return ConversationHandler.END

async def sell_title_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive item title"""
    context.user_data['sell_title'] = update.message.text
    
    await update.message.reply_text(
        "📋 **Great!** Now send me the **description**:\n\n"
        "Include details like:\n"
        "• Condition (new/used)\n"  
        "• Features & specifications\n"
        "• Reason for selling\n"
        "• Any defects",
        reply_markup=sell_flow_buttons()
    )
    
    return TYPING_DESCRIPTION

async def sell_description_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive item description"""
    context.user_data['sell_description'] = update.message.text
    
    await update.message.reply_text(
        "💰 Now send me the **price**:\n\n"
        "*Examples:*\n"
        "• '15000 ETB'\n"
        "• '100 USD'\n" 
        "• '5000 negotiable'\n"
        "• 'Free'",
        parse_mode='Markdown',
        reply_markup=sell_flow_buttons()
    )
    
    return TYPING_PRICE

async def sell_price_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive item price"""
    context.user_data['sell_price'] = update.message.text
    
    await update.message.reply_text(
        "📍 Finally, send me your **location**:\n\n"
        "*Examples:*\n"
        "• 'Addis Ababa, Bole'\n"
        "• 'Online Delivery'\n"
        "• 'City Mall pickup'\n"
        "• 'Specific address (share privately)'",
        parse_mode='Markdown',
        reply_markup=sell_flow_buttons()
    )
    
    return TYPING_LOCATION

async def sell_location_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Complete selling flow and save item"""
    try:
        context.user_data['sell_location'] = update.message.text
        user = update.message.from_user
        
        # Create item
        item = {
            'id': len(load_items()) + 1,
            'seller_id': user.id,
            'seller_name': user.first_name,
            'seller_username': user.username,
            'title': context.user_data.get('sell_title', ''),
            'description': context.user_data.get('sell_description', ''),
            'price': context.user_data.get('sell_price', ''),
            'category': context.user_data.get('sell_category', ''),
            'location': context.user_data.get('sell_location', ''),
            'timestamp': datetime.now().isoformat(),
            'active': True
        }
        
        # Save item
        items = load_items()
        items.append(item)
        save_items(items)
        track_item_listed()
        
        # Clear data
        context.user_data.clear()
        
        # Success message
        success_text = f"""
✅ **Item Listed Successfully!**

🏷️ **Title:** {item['title']}
📁 **Category:** {item['category']}  
💰 **Price:** {item['price']}
📍 **Location:** {item['location']}

**What's next?**
• Buyers can find your item in `/buy`
• View with `/myitems`
• Be ready for buyer messages!

🎉 *Thank you for using Merkato Marketplace!*
        """
        
        await update.message.reply_text(
            success_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛍️ Browse Other Items", callback_data="main_browse")],
                [InlineKeyboardButton("📋 View My Items", callback_data="main_myitems")],
                [InlineKeyboardButton("📦 List Another", callback_data="main_sell")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ])
        )
        
        return ConversationHandler.END
        
    except Exception as e:
        print(f"Error in sell_location_received: {e}")
        await update.message.reply_text(
            "❌ Error saving your item. Please try /sell again.",
            reply_markup=main_menu_buttons()
        )
        return ConversationHandler.END

async def cancel_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel selling flow"""
    context.user_data.clear()
    await show_message(update, "❌ Item listing cancelled.", main_menu_buttons())
    return ConversationHandler.END

# ========== MY ITEMS WITH BUTTONS ==========

async def show_my_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's items with management buttons"""
    try:
        user_id = update.effective_user.id
        items = get_user_items(user_id)
        
        if not items:
            text = "📭 **You haven't listed any items yet!**\n\nStart selling and make your first listing! 🎉"
            await show_message(update, text, InlineKeyboardMarkup([
                [InlineKeyboardButton("📦 List First Item", callback_data="main_sell")],
                [InlineKeyboardButton("🛍️ Browse Marketplace", callback_data="main_browse")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]))
            return
        
        text = f"📋 **Your Listed Items** ({len(items)} total)\n\n"
        for i, item in enumerate(items, 1):
            time_ago = get_time_ago(item.get('timestamp', ''))
            text += f"**{i}. {item['title']}**\n"
            text += f"   💰 {item['price']} | 📍 {item['location']}\n"
            text += f"   🏷️ {item['category']} | 🕒 {time_ago}\n\n"
        
        await show_message(update, text, InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 List New Item", callback_data="main_sell")],
            [InlineKeyboardButton("🛍️ Browse Marketplace", callback_data="main_browse")],
            [InlineKeyboardButton("🆕 Recent Listings", callback_data="main_recent")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]))
        
    except Exception as e:
        print(f"Error in show_my_items: {e}")
        await show_message(update, "❌ Error loading your items.", main_menu_buttons())

# ========== ADMIN COMMANDS WITH BUTTONS ==========

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin statistics with refresh button"""
    try:
        user_id = update.effective_user.id
        
        if not is_admin(user_id):
            await show_message(update, "❌ Admin access required.", main_menu_buttons())
            return
        
        analytics = load_analytics()
        items = load_items()
        
        stats_text = f"""
📊 **Admin Dashboard**

👥 **Users:** {analytics['total_users']}
📦 **Total Items:** {len(items)}
🔄 **Items Today:** {len([i for i in items if datetime.fromisoformat(i['timestamp']).date() == datetime.now().date()])}

🏷️ **Category Distribution:**
"""
        # Category stats
        category_stats = {}
        for item in items:
            cat = item.get('category', 'Unknown')
            category_stats[cat] = category_stats.get(cat, 0) + 1
        
        for category in CATEGORIES:
            count = category_stats.get(category, 0)
            stats_text += f"• {category}: {count}\n"
        
        stats_text += f"\n🕒 **Last Updated:** {datetime.now().strftime('%H:%M:%S')}"
        
        await show_message(update, stats_text, InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh Stats", callback_data="admin_refresh")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]))
        
    except Exception as e:
        print(f"Error in admin_stats: {e}")
        await show_message(update, "❌ Error loading stats.", main_menu_buttons())

# ========== UNIVERSAL BUTTON HANDLER ==========

async def handle_button_press(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main button handler for all inline keyboard actions"""
    try:
        query = update.callback_query
        data = query.data
        
        # Main menu actions
        if data == "main_menu":
            await start(update, context)
        elif data == "main_browse":
            await browse_categories(update, context)
        elif data == "main_sell":
            await start_sell_flow(update, context)
        elif data == "main_myitems":
            await show_my_items(update, context)
        elif data == "main_recent":
            await recent_command(update, context)
        elif data == "main_help":
            await help_command(update, context)
        
        # Browse actions
        elif data.startswith("browse_"):
            await show_category_items(update, context)
        elif data.startswith("nav_"):
            await navigate_items(update, context)
        elif data == "back_categories":
            await browse_categories(update, context)
        
        # Sell actions  
        elif data.startswith("sell_category_"):
            await sell_category_selected(update, context)
        elif data == "cancel_sell":
            await cancel_sell(update, context)
        
        # Admin actions
        elif data == "admin_refresh":
            await admin_stats(update, context)
        
        # Info actions
        elif data == "no_username":
            await query.answer("This seller hasn't set a Telegram username.", show_alert=True)
        elif data == "page_info":
            await query.answer()  # Silent acknowledgement
        
        else:
            await query.answer("❌ Action not available", show_alert=True)
            
    except Exception as e:
        print(f"Error in button handler: {e}")
        await query.answer("❌ Error processing action", show_alert=True)

# ========== HELPER FUNCTIONS ==========

async def show_message(update, text, reply_markup):
    """Helper to show messages for both messages and callback queries"""
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        query = update.callback_query
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# ========== MAIN APPLICATION ==========

def main():
    """Start the bot with all handlers"""
    print("🚀 Starting Enhanced Marketplace Bot with Buttons...")
    print(f"✅ Token: {TOKEN[:10]}...")
    print(f"✅ Admin ID: {ADMIN_USER_IDS[0]}")
    
    # Load initial data
    analytics = load_analytics()
    items = load_items()
    print(f"📊 Preloaded: {analytics['total_users']} users, {len(items)} items")
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Sell conversation handler
    sell_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('sell', start_sell_flow),
            CallbackQueryHandler(start_sell_flow, pattern='^main_sell$')
        ],
        states={
            SELECTING_CATEGORY: [CallbackQueryHandler(sell_category_selected, pattern='^sell_category_')],
            TYPING_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_title_received)],
            TYPING_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_description_received)],
            TYPING_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_price_received)],
            TYPING_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_location_received)],
        },
        fallbacks=[
            CommandHandler('cancel', cancel_sell),
            CallbackQueryHandler(cancel_sell, pattern='^cancel_sell$')
        ]
    )
    
    # Add all handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("buy", browse_categories))
    application.add_handler(CommandHandler("myitems", show_my_items))
    application.add_handler(CommandHandler("recent", recent_command))
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(sell_conv_handler)
    
    # Add handler for Marketplace button text message
    application.add_handler(MessageHandler(filters.Regex("^Marketplace$"), marketplace_button_handler))
    
    # Button handler (must be last)
    application.add_handler(CallbackQueryHandler(handle_button_press))
    
    # Start bot
    print("✅ Bot is running with full button functionality!")
    print("🎯 Users can navigate entirely with buttons")
    application.run_polling()

if __name__ == '__main__':
    main()