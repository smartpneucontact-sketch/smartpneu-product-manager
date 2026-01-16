from flask import Flask, render_template, request, jsonify, redirect, url_for
import shopify
import os
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from label_printer import TireLabelPrinter

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Shopify configuration
SHOPIFY_STORE = os.getenv('SHOPIFY_STORE')
SHOPIFY_ACCESS_TOKEN = os.getenv('SHOPIFY_ACCESS_TOKEN')
SHOP_URL = f"https://{SHOPIFY_STORE}.myshopify.com"

# Label printer configuration
PRINTER_NAME = os.getenv('PRINTER_NAME', 'HP_Color_LaserJet_MFP_M179fnw')
AUTO_PRINT_LABELS = os.getenv('AUTO_PRINT_LABELS', 'true').lower() == 'true'

# Initialize label printer
label_printer = TireLabelPrinter(printer_name=PRINTER_NAME)

# Initialize Shopify session
session = shopify.Session(SHOP_URL, "2024-01", SHOPIFY_ACCESS_TOKEN)
shopify.ShopifyResource.activate_session(session)

def extract_tire_data_from_product(product_data, product_obj):
    """
    Extract tire information from product data and Shopify product object
    for label printing
    """
    # Get metafields for tire specifications
    metafields = {}
    if hasattr(product_obj, 'metafields'):
        for mf in product_obj.metafields():
            metafields[mf.key] = mf.value
    
    # Get first variant for SKU
    sku = ''
    if hasattr(product_obj, 'variants') and len(product_obj.variants) > 0:
        sku = product_obj.variants[0].sku or str(product_obj.id)
    
    # Build product URL
    product_url = f"https://{SHOPIFY_STORE}.myshopify.com/products/{product_obj.handle}"
    
    # Extract tire data
    tire_data = {
        'brand': product_data.get('vendor', metafields.get('marque', '')),
        'model': product_data.get('title', ''),
        'largeur': metafields.get('largeur', product_data.get('largeur', '')),
        'hauteur': metafields.get('hauteur', product_data.get('hauteur', '')),
        'rayon': metafields.get('rayon', product_data.get('rayon', '')),
        'indice_charge': metafields.get('indice_charge', product_data.get('indice_charge', '')),
        'indice_vitesse': metafields.get('indice_vitesse', product_data.get('indice_vitesse', '')),
        'dot': metafields.get('dot', product_data.get('dot', '')),
        'profondeur': metafields.get('profondeur', product_data.get('profondeur', '')),
        'sku': sku,
        'product_url': product_url
    }
    
    return tire_data

@app.route('/')
def index():
    """Homepage with product creation form"""
    try:
        shop = shopify.Shop.current()
        connection_status = {
            'connected': True,
            'store_name': shop.name,
            'email': shop.email
        }
    except Exception as e:
        connection_status = {
            'connected': False,
            'error': str(e)
        }
    
    return render_template('index.html', connection_status=connection_status)

@app.route('/create-product', methods=['POST'])
def create_product():
    """Create a new product in Shopify and optionally print label"""
    try:
        # Get form data
        product_data = {
            'title': request.form.get('title'),
            'body_html': request.form.get('description'),
            'vendor': request.form.get('vendor', ''),
            'product_type': request.form.get('product_type', 'Tire'),
            'status': request.form.get('status', 'active'),
            'largeur': request.form.get('largeur', ''),
            'hauteur': request.form.get('hauteur', ''),
            'rayon': request.form.get('rayon', ''),
            'indice_charge': request.form.get('indice_charge', ''),
            'indice_vitesse': request.form.get('indice_vitesse', ''),
            'dot': request.form.get('dot', ''),
            'profondeur': request.form.get('profondeur', ''),
        }
        
        # Create product
        product = shopify.Product()
        product.title = product_data['title']
        product.body_html = product_data['body_html']
        product.vendor = product_data['vendor']
        product.product_type = product_data['product_type']
        product.status = product_data['status']
        
        # Add variant with price and SKU
        variant = shopify.Variant()
        variant.price = request.form.get('price', '0.00')
        variant.inventory_quantity = int(request.form.get('quantity', 0))
        variant.sku = request.form.get('sku', '')
        product.variants = [variant]
        
        # Handle image uploads
        images = []
        if 'images' in request.files:
            for image_file in request.files.getlist('images'):
                if image_file and image_file.filename:
                    image = shopify.Image()
                    image.attach_image(image_file.read())
                    images.append(image)
        
        if images:
            product.images = images
        
        # Save product to Shopify
        if product.save():
            product_id = product.id
            print(f"✅ Product created: {product.title} (ID: {product_id})")
            
            # Add metafields for tire specifications
            metafields_to_add = [
                ('largeur', product_data['largeur'], 'number_integer'),
                ('hauteur', product_data['hauteur'], 'number_integer'),
                ('rayon', product_data['rayon'], 'single_line_text_field'),
                ('indice_charge', product_data['indice_charge'], 'single_line_text_field'),
                ('indice_vitesse', product_data['indice_vitesse'], 'single_line_text_field'),
                ('dot', product_data['dot'], 'single_line_text_field'),
                ('profondeur', product_data['profondeur'], 'single_line_text_field'),
            ]
            
            for key, value, mf_type in metafields_to_add:
                if value:  # Only add if value exists
                    metafield = shopify.Metafield()
                    metafield.namespace = 'custom'
                    metafield.key = key
                    metafield.value = value
                    metafield.type = mf_type
                    product.add_metafield(metafield)
            
            # Generate and print label
            label_path = None
            if AUTO_PRINT_LABELS:
                try:
                    # Extract tire data for label
                    tire_data = extract_tire_data_from_product(product_data, product)
                    
                    # Generate and print label
                    label_path = label_printer.generate_and_print(
                        tire_data, 
                        print_enabled=True
                    )
                    print(f"🏷️  Label created: {label_path}")
                    
                except Exception as label_error:
                    print(f"⚠️  Label printing error: {str(label_error)}")
                    # Don't fail the whole request if label printing fails
            
            return jsonify({
                'success': True,
                'message': 'Product created successfully!',
                'product_id': product_id,
                'product_url': f"https://{SHOPIFY_STORE}.myshopify.com/admin/products/{product_id}",
                'label_generated': label_path is not None,
                'label_path': label_path
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to create product',
                'errors': product.errors.full_messages()
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/print-label/<product_id>', methods=['POST'])
def print_label(product_id):
    """Manually print label for an existing product"""
    try:
        # Fetch product from Shopify
        product = shopify.Product.find(product_id)
        
        if not product:
            return jsonify({
                'success': False,
                'message': 'Product not found'
            }), 404
        
        # Extract tire data
        tire_data = extract_tire_data_from_product({}, product)
        
        # Generate and print label
        label_path = label_printer.generate_and_print(tire_data, print_enabled=True)
        
        return jsonify({
            'success': True,
            'message': 'Label printed successfully',
            'label_path': label_path
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/test-label', methods=['GET'])
def test_label():
    """Test endpoint to generate a sample label without printing"""
    test_data = {
        'brand': 'Michelin',
        'model': 'Pilot Sport 4',
        'largeur': '225',
        'hauteur': '45',
        'rayon': '17',
        'indice_charge': '94',
        'indice_vitesse': 'Y',
        'dot': '3419',
        'profondeur': '7mm',
        'sku': 'TEST-001',
        'product_url': 'https://smartpneu.com/products/test'
    }
    
    # Generate without printing
    label_path = label_printer.generate_and_print(test_data, print_enabled=False)
    
    return jsonify({
        'success': True,
        'message': 'Test label generated (not printed)',
        'label_path': label_path,
        'note': f'Check {label_path} to verify label design'
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        shop = shopify.Shop.current()
        return jsonify({
            'status': 'healthy',
            'shopify_connected': True,
            'store': shop.name,
            'label_printing': AUTO_PRINT_LABELS
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'shopify_connected': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
