# --- 🩵 Python 3.13 Event Loop Fix ---
import asyncio
import sys
import logging
import sqlite3
import os
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

# --- Database Setup ---
def init_database():
    """Initialize database with proper tables"""
    try:
        conn = sqlite3.connect("marketplace.db")
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create items table with proper structure
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                price REAL NOT NULL,
                category TEXT NOT NULL,
                seller_id INTEGER NOT NULL,
                status TEXT DEFAULT "available",
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (seller_id) REFERENCES users (id)
            )
        ''')
        
        # Create index for better performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_items_seller_id 
            ON items (seller_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_items_status 
            ON items (status)
        ''')
        
        conn.commit()
        logger.info("✅ Database initialized successfully")
        
    except sqlite3.Error as e:
        logger.error(f"❌ Database initialization error: {e}")
        raise
    finally:
        if conn:
            conn.close()

def get_db_connection():
    """Get database connection with proper error handling"""
    try:
        conn = sqlite3.connect("marketplace.db")
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(f"❌ Database connection error: {e}")
        raise

def ensure_user_exists(user):
    """Ensure user exists in database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT OR IGNORE INTO users (id, username, first_name, last_name) VALUES (?, ?, ?, ?)',
            (user.id, user.username, user.first_name, user.last_name)
        )
        
        # Update user info if they already exist (in case they changed their profile)
        cursor.execute(
            'UPDATE users SET username=?, first_name=?, last_name=? WHERE id=?',
            (user.username, user.first_name, user.last_name, user.id)
        )
        
        conn.commit()
        logger.info(f"✅ User ensured: {user.id} - {user.first_name}")
        
    except sqlite3.Error as e:
        logger.error(f"❌ Error ensuring user exists: {e}")
    finally:
        if conn:
            conn.close()

def insert_item(title, description, price, category, seller_id):
    """Insert a new item into database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT INTO items (title, description, price, category, seller_id) VALUES (?, ?, ?, ?, ?)',
            (title, description, price, category, seller_id)
        )
        
        item_id = cursor.lastrowid
        conn.commit()
        logger.info(f"✅ Item inserted: {item_id} - {title}")
        return item_id
        
    except sqlite3.Error as e:
        logger.error(f"❌ Error inserting item: {e}")
        return None
    finally:
        if conn:
            conn.close()

def update_item_field(item_id, field, value):
    """Update specific field of an item"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Use parameterized query to prevent SQL injection
        cursor.execute(f'UPDATE items SET {field}=? WHERE id=?', (value, item_id))
        
        if cursor.rowcount == 0:
            logger.warning(f"⚠️ No item found with ID: {item_id}")
        else:
            logger.info(f"✅ Item {item_id} updated: {field} = {value}")
            
        conn.commit()
        
    except sqlite3.Error as e:
        logger.error(f"❌ Error updating item: {e}")
    finally:
        if conn:
            conn.close()

def delete_item(item_id):
    """Delete an item from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM items WHERE id=?', (item_id,))
        
        if cursor.rowcount == 0:
            logger.warning(f"⚠️ No item found to delete with ID: {item_id}")
        else:
            logger.info(f"✅ Item deleted: {item_id}")
            
        conn.commit()
        
    except sqlite3.Error as e:
        logger.error(f"❌ Error deleting item: {e}")
    finally:
        if conn:
            conn.close()

def get_user_items(user_id):
    """Get all items for a specific user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            '''SELECT id, title, description, price, category, status 
               FROM items WHERE seller_id=? 
               ORDER BY created_at DESC''',
            (user_id,)
        )
        
        items = cursor.fetchall()
        logger.info(f"✅ Retrieved {len(items)} items for user: {user_id}")
        return items
        
    except sqlite3.Error as e:
        logger.error(f"❌ Error getting user items: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_item_by_id(item_id):
    """Get a specific item by ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT id, title, description, price, category, status, seller_id FROM items WHERE id=?',
            (item_id,)
        )
        
        item = cursor.fetchone()
        return item
        
    except sqlite3.Error as e:
        logger.error(f"❌ Error getting item by ID: {e}")
        return None
    finally:
        if conn:
            conn.close()

def check_database_health():
    """Check if database is working properly"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check users table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        users_table_exists = cursor.fetchone() is not None
        
        # Check items table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='items'")
        items_table_exists = cursor.fetchone() is not None
        
        # Count records
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM items")
        item_count = cursor.fetchone()[0]
        
        conn.close()
        
        logger.info(f"🔍 Database Health Check:")
        logger.info(f"   Users table: {'✅' if users_table_exists else '❌'}")
        logger.info(f"   Items table: {'✅' if items_table_exists else '❌'}")
        logger.info(f"   Total users: {user_count}")
        logger.info(f"   Total items: {item_count}")
        
        return users_table_exists and items_table_exists
        
    except sqlite3.Error as e:
        logger.error(f"❌ Database health check failed: {e}")
        return False

# --- Start Command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user_exists(user)

    keyboard = [
        [InlineKeyboardButton("🛍️ Browse Marketplace", url=WEB_APP_URL)],
        [InlineKeyboardButton("➕ Add Item", callback_data="additem")],
        [InlineKeyboardButton("📦 My Items", callback_data="myitems")],
        [InlineKeyboardButton("🔍 Check DB", callback_data="checkdb")],
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

    if item_id:
        await update.message.reply_text(
            f"✅ Your item has been added!\n\n"
            f"📦 Title: {context.user_data['title']}\n"
            f"📝 Description: {context.user_data['description']}\n"
            f"💰 Price: ${context.user_data['price']:.2f}\n"
            f"📂 Category: {context.user_data['category']}\n\n"
            f"🌐 You can view it on the marketplace here: {WEB_APP_URL}"
        )
    else:
        await update.message.reply_text("❌ Failed to add item. Please try again.")
    
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
    await query.answer()
    
    user = update.effective_user
    items = get_user_items(user.id)

    if not items:
        await query.message.reply_text("📭 You have no items listed.")
        return

    header_text = f"📦 Your Listed Items ({len(items)} items):"
    await query.message.reply_text(header_text)

    for item in items:
        item_id = item['id']
        status_emoji = "✅" if item['status'] == 'available' else "💰"
        
        message_text = (
            f"{status_emoji} *{item['title']}*\n"
            f"💰 Price: ${item['price']:.2f}\n"
            f"📂 Category: {item['category']}\n"
            f"📝 Description: {item['description'][:100]}{'...' if len(item['description']) > 100 else ''}"
        )
        
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

    header_text = f"📦 Your Listed Items ({len(items)} items):"
    await update.message.reply_text(header_text)

    for item in items:
        item_id = item['id']
        status_emoji = "✅" if item['status'] == 'available' else "💰"
        
        message_text = (
            f"{status_emoji} *{item['title']}*\n"
            f"💰 Price: ${item['price']:.2f}\n"
            f"📂 Category: {item['category']}\n"
            f"📝 Description: {item['description'][:100]}{'...' if len(item['description']) > 100 else ''}"
        )
        
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

# --- Database Check Handler ---
async def check_database_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check database status"""
    query = update.callback_query
    await query.answer()
    
    is_healthy = check_database_health()
    
    if is_healthy:
        await query.message.reply_text("✅ Database is working properly!")
    else:
        await query.message.reply_text("❌ Database has issues. Check logs for details.")

# --- Delete Item Handler ---
async def delete_item_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle item deletion"""
    query = update.callback_query
    await query.answer()
    
    item_id = int(query.data.split("_")[1])
    user_id = update.effective_user.id
    
    item = get_item_by_id(item_id)
    if not item:
        await query.message.reply_text("❌ Item not found.")
        return
    
    if item['seller_id'] != user_id:
        await query.message.reply_text("❌ You can only delete your own items.")
        return
    
    delete_item(item_id)
    await query.message.reply_text("🗑️ Item deleted successfully.")

# --- Edit Item Flow ---
async def start_edit_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the edit item process"""
    query = update.callback_query
    await query.answer()
    
    item_id = int(query.data.split("_")[1])
    user_id = update.effective_user.id
    
    item = get_item_by_id(item_id)
    if not item:
        await query.message.reply_text("❌ Item not found.")
        return ConversationHandler.END
    
    if item['seller_id'] != user_id:
        await query.message.reply_text("❌ You can only edit your own items.")
        return ConversationHandler.END
    
    context.user_data['edit_item_id'] = item_id
    context.user_data['current_item'] = dict(item)
    
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

    update_item_field(item_id, field, value)
    
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

# --- Main Button Handler ---
async def main_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle main menu buttons"""
    query = update.callback_query
    await query.answer()
    
    data = query.data

    if data == "additem":
        await start_add_item(update, context)
    elif data == "myitems":
        await myitems_callback(update, context)
    elif data == "checkdb":
        await check_database_handler(update, context)

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
    
    if update and update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Sorry, something went wrong. Please try again."
        )

# --- Main Application Setup ---
async def main():
    # Initialize database first
    logger.info("🔄 Initializing database...")
    try:
        init_database()
        check_database_health()
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        return
    
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

    # Add handlers in correct order
    app.add_handler(add_item_conv)
    app.add_handler(edit_item_conv)

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myitems", myitems_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel_operation))

    # Callback query handlers
    app.add_handler(CallbackQueryHandler(delete_item_handler, pattern="^delete_"))
    app.add_handler(CallbackQueryHandler(main_button_handler, pattern="^(additem|myitems|checkdb)$"))

    # Test command
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