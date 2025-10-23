from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_connection

load_dotenv()
app = Flask(__name__)

@app.route('/')
def home():
    return render_template('telegram_index.html')

@app.route('/marketplace')
def marketplace():
    return render_template('telegram_marketplace.html')

@app.route('/add-item')
def add_item():
    return render_template('telegram_add_item.html')

@app.route('/dashboard')
def dashboard():
    return render_template('telegram_dashboard.html')

@app.route('/admin')
def admin():
    return render_template('users.html')



@app.route('/api/items', methods=['GET'])
def get_items():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT i.id, i.title, i.description, i.price, i.status, i.views, i.likes,
                   c.name as category, c.emoji, u.username as seller_name
            FROM items i
            LEFT JOIN categories c ON i.category_id = c.id
            LEFT JOIN users u ON i.seller_id = u.id
            WHERE i.status = 'available'
            ORDER BY i.created_at DESC
        ''')

        items = []
        for row in cursor.fetchall():
            items.append({
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'price': row[3],
                'status': row[4],
                'views': row[5],
                'likes': row[6],
                'category': row[7],
                'category_emoji': row[8],
                'seller': row[9] or 'Unknown'
            })

        conn.close()
        return jsonify(items)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/add-item', methods=['POST'])
def api_add_item():
    try:
        data = request.get_json()

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO items (title, description, price, category_id, seller_id, status)
            VALUES (?, ?, ?, ?, ?, 'available')
        ''', (
            data['title'],
            data['description'],
            data['price'],
            data['category_id'],
            1  # Mock user ID for web app
        ))

        item_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Item added successfully!',
            'item': {
                'id': item_id,
                'title': data['title'],
                'price': data['price']
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories', methods=['GET'])
def get_categories():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT id, name, emoji FROM categories ORDER BY name')
        categories = [{'id': row[0], 'name': row[1], 'emoji': row[2]} for row in cursor.fetchall()]

        conn.close()
        return jsonify(categories)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats/<int:user_id>', methods=['GET'])
def get_user_stats(user_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Get user stats
        cursor.execute('''
            SELECT
                COUNT(i.id) as total_items,
                SUM(CASE WHEN i.status = 'sold' THEN 1 ELSE 0 END) as sold_items,
                SUM(CASE WHEN i.status = 'sold' THEN i.price ELSE 0 END) as total_revenue,
                AVG(i.views) as avg_views
            FROM items i
            WHERE i.seller_id = ?
        ''', (user_id,))

        stats = cursor.fetchone()
        total_items, sold_items, total_revenue, avg_views = stats

        conn.close()

        return jsonify({
            'total_items': total_items or 0,
            'sold_items': sold_items or 0,
            'total_revenue': total_revenue or 0,
            'avg_views': avg_views or 0,
            'success_rate': (sold_items/total_items*100) if total_items else 0
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
