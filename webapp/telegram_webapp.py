from flask import Flask, render_template, request, jsonify
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect('marketplace.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def home():
    """Main page"""
    conn = get_db_connection()
    
    # Get platform stats
    total_items = conn.execute('SELECT COUNT(*) FROM items WHERE status = "available"').fetchone()[0]
    total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    
    # Get recent items
    recent_items = conn.execute('''
        SELECT i.*, c.name as category_name, c.emoji, u.username, u.first_name
        FROM items i
        JOIN categories c ON i.category_id = c.id
        JOIN users u ON i.seller_id = u.id
        WHERE i.status = 'available'
        ORDER BY i.created_at DESC
        LIMIT 3
    ''').fetchall()
    
    conn.close()
    
    return render_template('telegram_index.html', 
                         total_items=total_items,
                         total_users=total_users,
                         recent_items=recent_items)

@app.route('/marketplace')
def marketplace():
    """Browse all items"""
    conn = get_db_connection()
    
    items = conn.execute('''
        SELECT i.*, c.name as category_name, c.emoji, u.username, u.first_name
        FROM items i
        JOIN categories c ON i.category_id = c.id
        JOIN users u ON i.seller_id = u.id
        WHERE i.status = 'available'
        ORDER BY i.created_at DESC
    ''').fetchall()
    
    conn.close()
    
    return render_template('telegram_marketplace.html', items=items)

@app.route('/add_item')
def add_item():
    """Add item form"""
    conn = get_db_connection()
    categories = conn.execute('SELECT id, name, emoji FROM categories ORDER BY name').fetchall()
    conn.close()
    
    return render_template('telegram_add_item.html', categories=categories)

@app.route('/my_items')
def my_items():
    """User's items"""
    conn = get_db_connection()
    
    # For demo, show all items. In real app, filter by user_id from Telegram
    items = conn.execute('''
        SELECT i.*, c.name as category_name, c.emoji
        FROM items i
        JOIN categories c ON i.category_id = c.id
        ORDER BY i.created_at DESC
        LIMIT 10
    ''').fetchall()
    
    # Get stats
    stats = conn.execute('''
        SELECT 
            COUNT(*) as total_items,
            SUM(CASE WHEN status = 'sold' THEN 1 ELSE 0 END) as sold_items,
            SUM(CASE WHEN status = 'sold' THEN price ELSE 0 END) as revenue,
            SUM(views) as total_views,
            SUM(likes) as total_likes
        FROM items
    ''').fetchone()
    
    conn.close()
    
    return render_template('telegram_my_items.html', 
                         items=items, 
                         stats=dict(stats) if stats else {})

# API endpoints
@app.route('/api/items')
def api_items():
    """JSON API for items"""
    conn = get_db_connection()
    items = conn.execute('''
        SELECT i.*, c.name as category_name, c.emoji, u.username
        FROM items i
        JOIN categories c ON i.category_id = c.id
        JOIN users u ON i.seller_id = u.id
        WHERE i.status = 'available'
        ORDER BY i.created_at DESC
    ''').fetchall()
    conn.close()
    
    return jsonify([dict(item) for item in items])

@app.route('/api/categories')
def api_categories():
    """JSON API for categories"""
    conn = get_db_connection()
    categories = conn.execute('SELECT id, name, emoji FROM categories ORDER BY name').fetchall()
    conn.close()
    
    return jsonify([dict(cat) for cat in categories])

@app.route('/api/add_item', methods=['POST'])
def api_add_item():
    """API to add item from web app"""
    try:
        data = request.json
        conn = get_db_connection()
        
        conn.execute('''
            INSERT INTO items (title, description, price, category_id, seller_id, status)
            VALUES (?, ?, ?, ?, ?, 'available')
        ''', (
            data['title'],
            data['description'],
            data['price'],
            data['category_id'],
            data.get('user_id', 1)  # In real app, get from Telegram WebApp initData
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'status': 'success', 'message': 'Item added successfully!'})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/purchase', methods=['POST'])
def api_purchase():
    """Handle purchase from web app"""
    try:
        data = request.json
        conn = get_db_connection()
        
        # Get item details
        item = conn.execute('SELECT * FROM items WHERE id = ?', (data['item_id'],)).fetchone()
        
        if item:
            # Create order
            conn.execute('''
                INSERT INTO orders (item_id, buyer_id, seller_id, total_amount, status)
                VALUES (?, ?, ?, ?, 'completed')
            ''', (data['item_id'], data.get('user_id', 1), item['seller_id'], item['price']))
            
            # Mark item as sold
            conn.execute('UPDATE items SET status = "sold" WHERE id = ?', (data['item_id'],))
            
            conn.commit()
        
        conn.close()
        return jsonify({'status': 'success', 'message': 'Purchase completed!'})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)