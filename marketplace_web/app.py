from flask import Flask, render_template, jsonify, request, send_from_directory
import json
import os
import logging
from datetime import datetime
from flask_cors import CORS

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class MarketplaceWebApp:
    def __init__(self):
        self.items_file = '../marketplace_items.json'
        self.analytics_file = '../analytics.json'

    def get_items(self):
        """Get all marketplace items"""
        try:
            with open(self.items_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error("Items file not found")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return []

    def get_categories(self):
        """Get unique categories from items"""
        items = self.get_items()
        categories = set(item.get('category', 'other') for item in items)
        return sorted(categories)

    def update_analytics(self, metric):
        """Update web app analytics"""
        try:
            with open(self.analytics_file, 'r+') as f:
                analytics = json.load(f)
                analytics[metric] = analytics.get(metric, 0) + 1
                f.seek(0)
                json.dump(analytics, f, indent=2)
                f.truncate()
        except Exception as e:
            logger.error(f"Analytics update error: {e}")

marketplace = MarketplaceWebApp()

@app.route('/')
def index():
    """Main web app page"""
    marketplace.update_analytics('webapp_visits')
    return render_template('index.html')

@app.route('/api/items')
def get_items():
    """API endpoint to get all items"""
    category = request.args.get('category', 'all')
    search = request.args.get('search', '')
    
    items = marketplace.get_items()
    
    # Filter by category
    if category != 'all':
        items = [item for item in items if item.get('category') == category]
    
    # Filter by search
    if search:
        search_lower = search.lower()
        items = [item for item in items if 
                search_lower in item.get('name', '').lower() or 
                search_lower in item.get('description', '').lower()]
    
    return jsonify(items)

@app.route('/api/items/<item_id>')
def get_item(item_id):
    """API endpoint to get specific item"""
    items = marketplace.get_items()
    try:
        item_id = float(item_id)
        item = next((item for item in items if item.get('id') == item_id), None)
        if item:
            return jsonify(item)
        return jsonify({"error": "Item not found"}), 404
    except ValueError:
        return jsonify({"error": "Invalid item ID"}), 400

@app.route('/api/categories')
def get_categories():
    """API endpoint to get categories"""
    categories = marketplace.get_categories()
    return jsonify(categories)

@app.route('/api/stats')
def get_stats():
    """API endpoint to get marketplace stats"""
    items = marketplace.get_items()
    categories = marketplace.get_categories()
    
    stats = {
        'total_items': len(items),
        'categories_count': len(categories),
        'total_value': sum(item.get('price', 0) for item in items),
        'categories': categories
    }
    
    return jsonify(stats)

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

# Serve static files
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)