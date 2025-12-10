import os
import json
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
import requests
from werkzeug.utils import secure_filename
import base64
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this')

# Shopify Configuration
SHOPIFY_STORE = os.getenv('SHOPIFY_STORE', 'smartpneu')
SHOPIFY_ACCESS_TOKEN = os.getenv('SHOPIFY_ACCESS_TOKEN')
SHOPIFY_API_VERSION = '2024-01'

# File upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Create uploads folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load Brand and Model data from JSON file
def load_brands_models():
    json_path = os.path.join(os.path.dirname(__file__), 'brands_models.json')
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Load default description from HTML file
def load_default_description():
    html_path = os.path.join(os.path.dirname(__file__), 'default_description.html')
    with open(html_path, 'r', encoding='utf-8') as f:
        return f.read()

BRANDS_MODELS = load_brands_models()
DEFAULT_DESCRIPTION = load_default_description()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_shopify_headers():
    return {
        'X-Shopify-Access-Token': SHOPIFY_ACCESS_TOKEN,
        'Content-Type': 'application/json'
    }


def get_shopify_url(endpoint):
    return f"https://{SHOPIFY_STORE}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/{endpoint}"


def get_collections():
    """Fetch all custom collections and smart collections from Shopify"""
    collections = []
    
    # Get custom collections
    url = get_shopify_url('custom_collections.json')
    response = requests.get(url, headers=get_shopify_headers())
    if response.status_code == 200:
        collections.extend(response.json().get('custom_collections', []))
    
    # Get smart collections
    url = get_shopify_url('smart_collections.json')
    response = requests.get(url, headers=get_shopify_headers())
    if response.status_code == 200:
        collections.extend(response.json().get('smart_collections', []))
    
    return collections


def get_next_sku():
    """Fetch all products and find the highest numeric SKU, then return next one"""
    highest_sku = 0
    
    # Shopify API paginates products, so we need to fetch all pages
    url = get_shopify_url('products.json?limit=250&fields=id,variants')
    
    while url:
        response = requests.get(url, headers=get_shopify_headers())
        
        if response.status_code != 200:
            break
            
        products = response.json().get('products', [])
        
        for product in products:
            for variant in product.get('variants', []):
                sku = variant.get('sku', '')
                # Check if SKU is numeric
                if sku and sku.isdigit():
                    sku_num = int(sku)
                    if sku_num > highest_sku:
                        highest_sku = sku_num
        
        # Check for next page in Link header
        link_header = response.headers.get('Link', '')
        if 'rel="next"' in link_header:
            # Extract next page URL
            links = link_header.split(',')
            for link in links:
                if 'rel="next"' in link:
                    url = link.split(';')[0].strip('<> ')
                    break
        else:
            url = None
    
    return highest_sku + 1


def upload_image_to_shopify(product_id, image_path):
    """Upload an image to a Shopify product"""
    with open(image_path, 'rb') as img_file:
        encoded_image = base64.b64encode(img_file.read()).decode('utf-8')
    
    url = get_shopify_url(f'products/{product_id}/images.json')
    data = {
        'image': {
            'attachment': encoded_image
        }
    }
    
    response = requests.post(url, headers=get_shopify_headers(), json=data)
    return response.status_code == 200 or response.status_code == 201


def create_product(product_data, images=None):
    """Create a new product in Shopify"""
    url = get_shopify_url('products.json')
    
    # Build product payload
    product = {
        'product': {
            'title': product_data['title'],
            'body_html': product_data.get('description', ''),
            'vendor': product_data.get('vendor', ''),
            'product_type': product_data.get('product_type', 'Tire'),
            'status': product_data.get('status', 'draft'),
            'variants': [
                {
                    'price': product_data.get('price', '0.00'),
                    'compare_at_price': product_data.get('compare_at_price') or None,
                    'sku': product_data.get('sku', ''),
                    'barcode': product_data.get('barcode', ''),
                    'inventory_management': 'shopify',
                    'inventory_quantity': int(product_data.get('inventory_quantity', 0)),
                    'requires_shipping': True
                }
            ],
            'metafields': []
        }
    }
    
    # Add metafields for tire specifications
    if product_data.get('largeur'):
        product['product']['metafields'].append({
            'namespace': 'custom',
            'key': 'largeur',
            'value': int(product_data['largeur']),
            'type': 'number_integer'
        })
    
    if product_data.get('hauteur'):
        product['product']['metafields'].append({
            'namespace': 'custom',
            'key': 'hauteur',
            'value': int(product_data['hauteur']),
            'type': 'number_integer'
        })
    
    if product_data.get('rayon'):
        product['product']['metafields'].append({
            'namespace': 'custom',
            'key': 'rayon',
            'value': product_data['rayon'],
            'type': 'single_line_text_field'
        })
    
    # Create the product
    response = requests.post(url, headers=get_shopify_headers(), json=product)
    
    if response.status_code in [200, 201]:
        created_product = response.json().get('product', {})
        product_id = created_product.get('id')
        
        # Upload images if provided
        if images and product_id:
            for image_path in images:
                upload_image_to_shopify(product_id, image_path)
        
        # Add to collection if specified
        if product_data.get('collection_id') and product_id:
            add_to_collection(product_id, product_data['collection_id'])
        
        return {'success': True, 'product': created_product}
    else:
        return {'success': False, 'error': response.json()}


def add_to_collection(product_id, collection_id):
    """Add a product to a collection"""
    url = get_shopify_url('collects.json')
    data = {
        'collect': {
            'product_id': product_id,
            'collection_id': int(collection_id)
        }
    }
    response = requests.post(url, headers=get_shopify_headers(), json=data)
    return response.status_code in [200, 201]


@app.route('/')
def index():
    """Main page with the product creation form"""
    collections = get_collections()
    next_sku = get_next_sku()
    return render_template('index.html', collections=collections, next_sku=next_sku, brands_models=BRANDS_MODELS, default_description=DEFAULT_DESCRIPTION)


@app.route('/api/get-models/<brand>')
def get_models(brand):
    """Return models for a specific brand"""
    models = BRANDS_MODELS.get(brand, [])
    return jsonify(models)


@app.route('/create-product', methods=['POST'])
def create_product_route():
    """Handle product creation form submission"""
    try:
        # Get form data
        product_data = {
            'title': request.form.get('title'),
            'description': request.form.get('description'),
            'price': request.form.get('price'),
            'compare_at_price': request.form.get('compare_at_price'),
            'sku': request.form.get('sku'),
            'barcode': request.form.get('barcode'),
            'vendor': request.form.get('vendor'),
            'product_type': request.form.get('product_type', 'Tire'),
            'inventory_quantity': request.form.get('inventory_quantity', 0),
            'largeur': request.form.get('largeur'),
            'hauteur': request.form.get('hauteur'),
            'rayon': request.form.get('rayon'),
            'collection_id': request.form.get('collection_id'),
            'status': request.form.get('status', 'draft')
        }
        
        # Handle image uploads
        images = []
        if 'images' in request.files:
            files = request.files.getlist('images')
            for file in files:
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    images.append(filepath)
        
        # Create the product
        result = create_product(product_data, images)
        
        # Clean up uploaded files
        for image_path in images:
            if os.path.exists(image_path):
                os.remove(image_path)
        
        if result['success']:
            flash(f"Product '{product_data['title']}' created successfully!", 'success')
            return redirect(url_for('index'))
        else:
            flash(f"Error creating product: {result['error']}", 'error')
            return redirect(url_for('index'))
            
    except Exception as e:
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('index'))


@app.route('/api/test-connection')
def test_connection():
    """Test the Shopify API connection"""
    try:
        url = get_shopify_url('shop.json')
        response = requests.get(url, headers=get_shopify_headers())
        
        if response.status_code == 200:
            shop_data = response.json().get('shop', {})
            return jsonify({
                'success': True,
                'shop_name': shop_data.get('name'),
                'domain': shop_data.get('domain')
            })
        else:
            return jsonify({
                'success': False,
                'error': f"HTTP {response.status_code}: {response.text}"
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


if __name__ == '__main__':
    if not SHOPIFY_ACCESS_TOKEN:
        print("⚠️  Warning: SHOPIFY_ACCESS_TOKEN not set in .env file")
    app.run(debug=True, port=5000)
