from flask import Flask, render_template, request, jsonify
import os
from dotenv import load_dotenv

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
    # Mock data for testing
    items = [
        {
            'id': 1,
            'title': 'Sample Item 1',
            'price': 29.99,
            'description': 'A great item for testing',
            'category': 'Electronics',
            'seller': 'Test Seller'
        },
        {
            'id': 2,
            'title': 'Sample Item 2',
            'price': 49.99,
            'description': 'Another test item',
            'category': 'Books',
            'seller': 'Another Seller'
        }
    ]
    return jsonify(items)

@app.route('/api/add-item', methods=['POST'])
def api_add_item():
    data = request.get_json()
    # Mock response
    return jsonify({
        'success': True,
        'message': 'Item added successfully!',
        'item': {
            'id': 999,
            'title': data.get('title'),
            'price': data.get('price')
        }
    })

if __name__ == '__main__':
    app.run(debug=True, port=5001)
