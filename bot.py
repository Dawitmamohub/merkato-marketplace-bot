# --- 🩵 Python 3.13 Event Loop Fix ---
import asyncio
import sys
import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    ConversationHandler, MessageHandler, filters, CallbackQueryHandler
)
import nest_asyncio

# Fix for Windows / Python 3.13
if sys.version_info >= (3, 13):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
nest_asyncio.apply()

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8257080955:AAHtlkZOLi8x0gstptCm2wcVN3lNHS5ZAFw"
WEB_APP_URL = "https://thirty-hands-rule.loca.lt/marketplace"

# --- Conversation states ---
TITLE, DESCRIPTION, PRICE, CATEGORY, EDIT_FIELD, NEW_VALUE = range(6)

# --- Database ---
def get_db_connection():
    conn = sqlite3.connect("marketplace.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize database tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT
        )
    ''')
    
    # Create items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            price REAL,
            category TEXT,
            seller_id INTEGER,
            status TEXT DEFAULT "available",
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def ensure_user_exists(user):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT OR IGNORE INTO users (id, username, first_name, last_name) VALUES (?, ?, ?, ?)',
        (user.id, user.username, user.first_name, user.last_name)
    )
    conn.commit()
    conn.close()

def insert_item(title, description, price, category, seller_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO items (title, description, price, category, seller_id) VALUES (?, ?, ?, ?, ?)',
        (title, description, price, category, seller_id)
    )
    item_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return item_id

def update_item_field(item_id, field, value):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f'UPDATE items SET {field}=? WHERE id=?', (value, item_id))
    conn.commit()
    conn.close()

def delete_item(item_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM items WHERE id=?', (item_id,))
    conn.commit()
    conn.close()

def get_user_items(user_id):
    """Get all items for a specific user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, title, description, price, category, status FROM items WHERE seller_id=? ORDER BY id DESC',
        (user_id,)
    )
    items = cursor.fetchall()
    conn.close()
    return items

def get_item_by_id(item_id):
    """Get a specific item by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, title, description, price, category, status, seller_id FROM items WHERE id=?',
        (item_id,)
    )
    item = cursor.fetchone()
    conn.close()
    return item

# --- Start Command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user_exists(user)

    keyboard = [
        [InlineKeyboardButton("🛍️ Browse Marketplace", url=WEB_APP_URL)],
        [InlineKeyboardButton("➕ Add Item", callback_data="additem")],
        [InlineKeyboardButton("📦 My Items", callback_data="myitems")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"👋 Welcome {user.first_name}!\nUse the buttons below to start.",
        reply_markup=reply_markup
    )

# --- Add Item Conversation ---
async def start_add_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the add item conversation"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.message.reply_text(
            "➕ Let's add a new item!\n\nPlease enter the *title* of your item:",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "➕ Let's add a new item!\n\nPlease enter the *title* of your item:",
            parse_mode="Markdown"
        )
    
    return TITLE

async def receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['title'] = update.message.text
    await update.message.reply_text("Enter the *description* of your item:", parse_mode="Markdown")
    return DESCRIPTION

async def receive_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    await update.message.reply_text("Enter the *price* of your item (numbers only):", parse_mode="Markdown")
    return PRICE

async def receive_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text)
        if price <= 0:
            await update.message.reply_text("❌ Price must be greater than 0. Please enter a valid price:")
            return PRICE
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number for the price:")
        return PRICE
    
    context.user_data['price'] = price
    await update.message.reply_text("Enter the *category* of your item:", parse_mode="Markdown")
    return CATEGORY

async def receive_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['category'] = update.message.text
    user = update.effective_user

    item_id = insert_item(
        context.user_data['title'],
        context.user_data['description'],
        context.user_data['price'],
        context.user_data['category'],
        user.id
    )

    await update.message.reply_text(
        f"✅ Your item has been added!\n\n"
        f"📦 Title: {context.user_data['title']}\n"
        f"📝 Description: {context.user_data['description']}\n"
        f"💰 Price: ${context.user_data['price']:.2f}\n"
        f"📂 Category: {context.user_data['category']}\n\n"
        f"🌐 You can view it on the marketplace here: {WEB_APP_URL}"
    )
    
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_add_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Add Item canceled.")
    context.user_data.clear()
    return ConversationHandler.END

# --- My Items Functionality ---
async def myitems_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle My Items button callback"""
    query = update.callback_query
    await query.answer()  # CRITICAL: This removes the loading state
    
    user = update.effective_user
    items = get_user_items(user.id)

    if not items:
        await query.message.reply_text("📭 You have no items listed.")
        return

    # Send header message
    header_text = f"📦 Your Listed Items ({len(items)} items):"
    await query.message.reply_text(header_text)

    # Display each item with edit/delete buttons
    for item in items:
        item_id = item['id']
        status_emoji = "✅" if item['status'] == 'available' else "💰"
        
        # Format the item message
        message_text = (
            f"{status_emoji} *{item['title']}*\n"
            f"💰 Price: ${item['price']:.2f}\n"
            f"📂 Category: {item['category']}\n"
            f"📝 Description: {item['description'][:100]}{'...' if len(item['description']) > 100 else ''}"
        )
        
        # Create inline keyboard for each item
        keyboard = [
            [
                InlineKeyboardButton("✏️ Edit", callback_data=f"edit_{item_id}"),
                InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_{item_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            message_text, 
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

async def myitems_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /myitems command"""
    user = update.effective_user
    items = get_user_items(user.id)

    if not items:
        await update.message.reply_text("📭 You have no items listed.")
        return

    # Send header message
    header_text = f"📦 Your Listed Items ({len(items)} items):"
    await update.message.reply_text(header_text)

    # Display each item with edit/delete buttons
    for item in items:
        item_id = item['id']
        status_emoji = "✅" if item['status'] == 'available' else "💰"
        
        # Format the item message
        message_text = (
            f"{status_emoji} *{item['title']}*\n"
            f"💰 Price: ${item['price']:.2f}\n"
            f"📂 Category: {item['category']}\n"
            f"📝 Description: {item['description'][:100]}{'...' if len(item['description']) > 100 else ''}"
        )
        
        # Create inline keyboard for each item
        keyboard = [
            [
                InlineKeyboardButton("✏️ Edit", callback_data=f"edit_{item_id}"),
                InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_{item_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message_text, 
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

# --- Delete Item Handler ---
async def delete_item_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle item deletion"""
    query = update.callback_query
    await query.answer()
    
    item_id = int(query.data.split("_")[1])
    user_id = update.effective_user.id
    
    # Verify the item belongs to the user
    item = get_item_by_id(item_id)
    if not item:
        await query.message.reply_text("❌ Item not found.")
        return
    
    if item['seller_id'] != user_id:
        await query.message.reply_text("❌ You can only delete your own items.")
        return
    
    # Delete the item
    delete_item(item_id)
    await query.message.reply_text("🗑️ Item deleted successfully.")

# --- Edit Item Flow ---
async def start_edit_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the edit item process"""
    query = update.callback_query
    await query.answer()
    
    item_id = int(query.data.split("_")[1])
    user_id = update.effective_user.id
    
    # Verify the item belongs to the user
    item = get_item_by_id(item_id)
    if not item:
        await query.message.reply_text("❌ Item not found.")
        return ConversationHandler.END
    
    if item['seller_id'] != user_id:
        await query.message.reply_text("❌ You can only edit your own items.")
        return ConversationHandler.END
    
    # Store item info in context
    context.user_data['edit_item_id'] = item_id
    context.user_data['current_item'] = dict(item)
    
    # Show edit options
    keyboard = [
        [
            InlineKeyboardButton("📝 Title", callback_data="field_title"),
            InlineKeyboardButton("📄 Description", callback_data="field_description")
        ],
        [
            InlineKeyboardButton("💰 Price", callback_data="field_price"),
            InlineKeyboardButton("📂 Category", callback_data="field_category")
        ],
        [
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")
        ]
    ]
    
    current_item = context.user_data['current_item']
    preview_text = (
        f"✏️ Editing: *{current_item['title']}*\n\n"
        f"Current details:\n"
        f"• Title: {current_item['title']}\n"
        f"• Description: {current_item['description']}\n"
        f"• Price: ${current_item['price']:.2f}\n"
        f"• Category: {current_item['category']}\n\n"
        f"Select what you want to edit:"
    )
    
    await query.message.reply_text(
        preview_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return EDIT_FIELD

async def select_edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Let user select which field to edit"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel_edit":
        await query.message.reply_text("❌ Edit canceled.")
        context.user_data.clear()
        return ConversationHandler.END
    
    field = query.data.split("_")[1]
    context.user_data['edit_field'] = field
    
    field_prompts = {
        'title': 'Enter the new title:',
        'description': 'Enter the new description:',
        'price': 'Enter the new price (numbers only):',
        'category': 'Enter the new category:'
    }
    
    await query.message.reply_text(field_prompts[field])
    return NEW_VALUE

async def receive_new_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and validate the new value for the field"""
    item_id = context.user_data.get('edit_item_id')
    field = context.user_data.get('edit_field')
    value = update.message.text.strip()

    if not value:
        await update.message.reply_text("❌ Value cannot be empty. Please enter a valid value:")
        return NEW_VALUE

    if field == "price":
        try:
            value = float(value)
            if value <= 0:
                await update.message.reply_text("❌ Price must be greater than 0. Please enter a valid price:")
                return NEW_VALUE
        except ValueError:
            await update.message.reply_text("❌ Price must be a number. Please enter a valid price:")
            return NEW_VALUE

    # Update the item in database
    update_item_field(item_id, field, value)
    
    # Get updated item for confirmation
    updated_item = get_item_by_id(item_id)
    
    await update.message.reply_text(
        f"✅ {field.capitalize()} updated successfully!\n\n"
        f"Updated item:\n"
        f"📦 Title: {updated_item['title']}\n"
        f"📝 Description: {updated_item['description']}\n"
        f"💰 Price: ${updated_item['price']:.2f}\n"
        f"📂 Category: {updated_item['category']}"
    )
    
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the edit operation"""
    await update.message.reply_text("❌ Edit canceled.")
    context.user_data.clear()
    return ConversationHandler.END

# --- Main Menu Button Handler ---
async def main_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle main menu buttons"""
    query = update.callback_query
    await query.answer()  # Always answer callback queries
    
    data = query.data

    if data == "additem":
        # Start add item conversation
        await start_add_item(update, context)
    elif data == "myitems":
        await myitems_callback(update, context)

# --- Help Command ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message"""
    help_text = (
        "🤖 *Marketplace Bot Help*\n\n"
        "*/start* - Show main menu\n"
        "*/additem* - Add a new item to sell\n" 
        "*/myitems* - View and manage your items\n"
        "*/help* - Show this help message\n\n"
        "You can also use the buttons in the main menu!"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

# --- Cancel any operation ---
async def cancel_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel any current operation"""
    await update.message.reply_text("❌ Operation canceled.")
    context.user_data.clear()
    return ConversationHandler.END

# --- Error Handler ---
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors and send a message to the user"""
    logger.error(f"Exception while handling an update: {context.error}")
    
    # Send a message to the user
    if update and update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Sorry, something went wrong. Please try again."
        )

# --- Main Application Setup ---
async def main():
    # Initialize database
    init_database()
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add error handler
    app.add_error_handler(error_handler)

    # Add Item Conversation Handler
    add_item_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_add_item, pattern="^additem$"),
            CommandHandler("additem", start_add_item)
        ],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_title)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_description)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_price)],
            CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_category)],
        },
        fallbacks=[CommandHandler("cancel", cancel_add_item)],
        name="add_item_conversation"
    )

    # Edit Item Conversation Handler
    edit_item_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_edit_item, pattern="^edit_")],
        states={
            EDIT_FIELD: [CallbackQueryHandler(select_edit_field, pattern="^field_|^cancel_edit")],
            NEW_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_value)],
        },
        fallbacks=[CommandHandler("cancel", cancel_edit)],
        name="edit_item_conversation"
    )

    # Add handlers in correct order (conversation handlers first)
    app.add_handler(add_item_conv)
    app.add_handler(edit_item_conv)

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myitems", myitems_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel_operation))

    # Callback query handlers - ORDER MATTERS!
    # More specific patterns first
    app.add_handler(CallbackQueryHandler(delete_item_handler, pattern="^delete_"))
    app.add_handler(CallbackQueryHandler(main_button_handler, pattern="^(additem|myitems)$"))

    # Test command for debugging
    async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("✅ Bot is working! Use /start to see the main menu.")
    
    app.add_handler(CommandHandler("test", test_command))

    # Log bot info
    bot_info = await app.bot.get_me()
    logger.info(f"🤖 Bot connected as: @{bot_info.username}")

    # Start polling
    logger.info("🚀 Starting bot polling...")
    await app.run_polling(drop_pending_updates=True)

# --- Entry point ---
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Bot stopped manually.")
    except Exception as e:
        logger.error(f"❌ Bot crashed with error: {e}")