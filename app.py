from flask import Flask, render_template, request, jsonify, redirect, url_for
import shopify
import os
import json
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from label_printer import TireLabelPrinter

# Load environment variables
load_dotenv()


# ============================================================
# PUBLICATION HANDLER - Auto-publish to all sales channels
# ============================================================

def get_all_publications():
    """
    Fetch all available publications (sales channels) using GraphQL.
    Returns a list of publication IDs and names.
    """
    query = """
    {
        publications(first: 10) {
            edges {
                node {
                    id
                    name
                }
            }
        }
    }
    """
    
    result = shopify.GraphQL().execute(query)
    data = json.loads(result)
    
    if 'errors' in data:
        print(f"❌ Error fetching publications: {data['errors']}")
        return []
    
    publications = []
    for edge in data.get('data', {}).get('publications', {}).get('edges', []):
        node = edge['node']
        publications.append({
            'id': node['id'],
            'name': node['name']
        })
    
    return publications


def publish_product_to_all_channels(product_id):
    """
    Publish a product to all available sales channels.
    
    Args:
        product_id: The numeric Shopify product ID (e.g., 1234567890)
                   Will be converted to GID format automatically.
    
    Returns:
        dict with 'success' boolean and 'results' list
    """
    # Convert numeric ID to GID format if needed
    if not str(product_id).startswith('gid://'):
        product_gid = f"gid://shopify/Product/{product_id}"
    else:
        product_gid = product_id
    
    # Get all publications
    publications = get_all_publications()
    
    if not publications:
        return {
            'success': False,
            'error': 'No publications found',
            'results': []
        }
    
    print(f"📢 Found {len(publications)} sales channels:")
    for pub in publications:
        print(f"   - {pub['name']}")
    
    results = []
    
    # Publish to each channel
    for publication in publications:
        mutation = """
        mutation publishablePublish($id: ID!, $input: [PublicationInput!]!) {
            publishablePublish(id: $id, input: $input) {
                publishable {
                    availablePublicationsCount {
                        count
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        variables = {
            "id": product_gid,
            "input": [
                {
                    "publicationId": publication['id']
                }
            ]
        }
        
        result = shopify.GraphQL().execute(mutation, variables=variables)
        data = json.loads(result)
        
        if 'errors' in data:
            results.append({
                'publication': publication['name'],
                'success': False,
                'error': data['errors']
            })
            print(f"   ❌ Failed: {publication['name']}")
        else:
            user_errors = data.get('data', {}).get('publishablePublish', {}).get('userErrors', [])
            if user_errors:
                results.append({
                    'publication': publication['name'],
                    'success': False,
                    'error': user_errors
                })
                print(f"   ❌ Failed: {publication['name']} - {user_errors}")
            else:
                results.append({
                    'publication': publication['name'],
                    'success': True
                })
                print(f"   ✅ Published to: {publication['name']}")
    
    all_success = all(r['success'] for r in results)
    
    return {
        'success': all_success,
        'results': results,
        'channels_count': len(publications)
    }


# ============================================================
print("=" * 50)
print("DEBUG: Environment Variables")
print(f"SHOPIFY_STORE: {os.getenv('SHOPIFY_STORE')}")
print(f"SHOPIFY_ACCESS_TOKEN: {os.getenv('SHOPIFY_ACCESS_TOKEN')[:15]}...") # Only show first 15 chars
print(f"SHOP_URL will be: https://{os.getenv('SHOPIFY_STORE')}.myshopify.com")
print("=" * 50)

# CREATE THE APP FIRST! ← This must come before @app.route
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Shopify configuration
SHOPIFY_STORE = os.getenv('SHOPIFY_STORE')
SHOPIFY_ACCESS_TOKEN = os.getenv('SHOPIFY_ACCESS_TOKEN')
SHOP_URL = f"https://{SHOPIFY_STORE}.myshopify.com"

# Label printer configuration
PRINTER_NAME = os.getenv('PRINTER_NAME', 'HP_Color_LaserJet_MFP_M179fnw')
AUTO_PRINT_LABELS = os.getenv('AUTO_PRINT_LABELS', 'true').lower() == 'true'
PRINT_BLACK_AND_WHITE = os.getenv('PRINT_BLACK_AND_WHITE', 'true').lower() == 'true'

# Initialize label printer (B&W mode for testing)
label_printer = TireLabelPrinter(printer_name=PRINTER_NAME, black_and_white=PRINT_BLACK_AND_WHITE)

# Initialize Shopify session with proper configuration
API_VERSION = "2023-04"  # Add this as a constant at the top

# Then use it like:
session = shopify.Session(SHOP_URL, API_VERSION, SHOPIFY_ACCESS_TOKEN)

# Activate session and set up connection
shopify.ShopifyResource.activate_session(session)
shopify.ShopifyResource.site = f"{SHOP_URL}/admin/api/{API_VERSION}"

def extract_tire_data_from_product(product_data, product_obj):
    """
    Extract tire information from product data and Shopify product object
    for label printing
    """
    # Get first variant for SKU
    sku = product_data.get('sku', '')
    if not sku and hasattr(product_obj, 'variants') and len(product_obj.variants) > 0:
        sku = product_obj.variants[0].sku or str(product_obj.id)
    
    # Build product URL
    product_url = f"https://{SHOPIFY_STORE}.myshopify.com/products/{product_obj.handle}"
    
    # Extract tire data - ensure all values are strings
    tire_data = {
        'brand': str(product_data.get('vendor', '') or ''),
        'model': str(product_data.get('model', '') or product_data.get('title', '') or ''),
        'largeur': str(product_data.get('largeur', '') or ''),
        'hauteur': str(product_data.get('hauteur', '') or ''),
        'rayon': str(product_data.get('rayon', '') or ''),
        'indice_charge': str(product_data.get('load_index', '') or ''),
        'indice_vitesse': str(product_data.get('speed_index', '') or ''),
        'dot': str(product_data.get('dot', '') or ''),
        'profondeur': str(product_data.get('tread_depth', '') or ''),
        'sku': str(sku),
        'product_url': product_url
    }
    
    return tire_data

# NOW you can use @app.route


def get_next_sku():
    """Get the next available SKU by finding the highest numeric SKU and adding 1"""
    try:
        # Activate session with stable API version
        API_VERSION = "2023-04"  # Use stable version
        session = shopify.Session(SHOP_URL, API_VERSION, SHOPIFY_ACCESS_TOKEN)
        shopify.ShopifyResource.activate_session(session)
        
        # Get all products with their variants
        all_skus = []
        products = shopify.Product.find(limit=250)
        
        while products:
            for product in products:
                for variant in product.variants:
                    if variant.sku:
                        # Try to extract numeric part of SKU
                        try:
                            sku_num = int(variant.sku)
                            all_skus.append(sku_num)
                        except ValueError:
                            # SKU is not purely numeric, try to extract numbers
                            import re
                            numbers = re.findall(r'\d+', variant.sku)
                            if numbers:
                                all_skus.append(int(numbers[-1]))
            
            # Check for more pages
            if products.has_next_page():
                products = products.next_page()
            else:
                break
        
        if all_skus:
            next_sku = max(all_skus) + 1
            print(f"✅ Highest SKU found: {max(all_skus)}, next SKU: {next_sku}")
            return str(next_sku)
        else:
            print("⚠️ No numeric SKUs found, starting at 1001")
            return "1001"
            
    except Exception as e:
        print(f"❌ Error getting next SKU: {e}")
        return "1001"




@app.route('/')
def index():
    """Homepage with product creation form"""
    
    # ✅ ACTIVATE SESSION FIRST
    session = shopify.Session(SHOP_URL, "unstable", SHOPIFY_ACCESS_TOKEN)
    shopify.ShopifyResource.activate_session(session)
    
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
    
    # Load brands and models from JSON file
    try:
        with open('brands_models.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        brands_models = {}
        full_tire_data = {}
        
        if 'brands' in data:
            for brand in data['brands']:
                brand_name = brand['name']
                brands_models[brand_name] = [model['name'] for model in brand['models']]
                full_tire_data[brand_name] = brand['models']
        else:
            brands_models = data
            
    except FileNotFoundError:
        brands_models = {}
        full_tire_data = {}
    
    # Fetch collections from Shopify
    collections = []
    try:
        custom_collections = shopify.CustomCollection.find()
        smart_collections = shopify.SmartCollection.find()
        collections = list(custom_collections) + list(smart_collections)
        print(f"✅ Loaded {len(collections)} collections")
    except Exception as e:
        print(f"❌ Error loading collections: {e}")
        collections = []
    
    # Load default description
    default_description = ""
    try:
        with open('default_description.html', 'r', encoding='utf-8') as f:
            default_description = f.read()
    except FileNotFoundError:
        pass
    
    # Get next SKU
    next_sku = ""
    try:
        next_sku = get_next_sku()
    except:
        next_sku = "1001"
    
    return render_template('index.html', 
                         connection_status=connection_status,
                         brands_models=brands_models,
                         collections=collections,
                         default_description=default_description,
                         next_sku=next_sku)


@app.route('/api/test-connection')
def test_connection():
    """Test Shopify connection endpoint"""
    print("\n" + "="*50)
    print("🔍 TESTING SHOPIFY CONNECTION")
    print(f"Store: {SHOPIFY_STORE}")
    print(f"Shop URL: {SHOP_URL}")
    print(f"Token (first 15 chars): {SHOPIFY_ACCESS_TOKEN[:15]}...")
    print("="*50)
    
    try:
        # Create a fresh session for this request
        test_session = shopify.Session(SHOP_URL, "unstable", SHOPIFY_ACCESS_TOKEN)
        shopify.ShopifyResource.activate_session(test_session)
        
        print("✅ Session activated, attempting to fetch shop...")
        
        shop = shopify.Shop.current()
        
        print("✅ CONNECTION SUCCESSFUL!")
        print(f"Shop Name: {shop.name}")
        print(f"Shop Email: {shop.email}")
        print("="*50 + "\n")
        
        return jsonify({
            'success': True,
            'connected': True,
            'store_name': shop.name,
            'email': shop.email
        })
        
    except Exception as e:
        print("❌ CONNECTION FAILED!")
        print(f"Error: {str(e)}")
        print("\nFull traceback:")
        import traceback
        traceback.print_exc()
        print("="*50 + "\n")
        
        return jsonify({
            'success': False,
            'connected': False,
            'error': str(e)
        }), 500

@app.route('/api/model-details/<brand>/<model>')
def get_model_details(brand, model):
    """Get detailed tire model information"""
    try:
        with open('brands_models.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Find the brand
        for brand_data in data['brands']:
            if brand_data['name'] == brand:
                # Find the model
                for model_data in brand_data['models']:
                    if model_data['name'] == model:
                        return jsonify({
                            'success': True,
                            'model': model_data
                        })
        
        return jsonify({
            'success': False,
            'error': 'Model not found'
        }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/create-product', methods=['POST'])
def create_product():
    """Create a new product in Shopify and optionally print label"""
    # ✅ ACTIVATE SESSION FIRST
    session = shopify.Session(SHOP_URL, "2023-04", SHOPIFY_ACCESS_TOKEN)
    shopify.ShopifyResource.activate_session(session)
    try:
        # Get form data - include ALL fields
        product_data = {
            'title': request.form.get('title'),
            'body_html': request.form.get('description'),
            'vendor': request.form.get('vendor', ''),
            'model': request.form.get('model', ''),
            'product_type': request.form.get('product_type', 'Tire'),
            'status': request.form.get('status', 'active'),
            'largeur': request.form.get('largeur', ''),
            'hauteur': request.form.get('hauteur', ''),
            'rayon': request.form.get('rayon', ''),
            'load_index': request.form.get('load_index', ''),
            'speed_index': request.form.get('speed_index', ''),
            'dot': request.form.get('dot', ''),
            'tread_depth': request.form.get('tread_depth', ''),
            'tire_count': request.form.get('tire_count', ''),
            'commercial_tire': request.form.get('commercial_tire', ''),
            'tire_provider': request.form.get('tire_provider', ''),
            'arrival_date': request.form.get('arrival_date', ''),
            'item_condition': request.form.get('item_condition', ''),
            'price_difference_to_new': request.form.get('price_difference_to_new', ''),
            'sku': request.form.get('sku', ''),
            'price': request.form.get('price', '0.00'),
        }

        # DEBUG: Print all form data
        print("=" * 50)
        print("📋 FORM DATA RECEIVED:")
        for key, value in request.form.items():
            print(f"  {key}: {value}")
        print("=" * 50)
        
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
            
            # Add metafields for tire specifications (match Shopify metafield types)
            metafields_to_add = [
                ('largeur', request.form.get('largeur'), 'number_integer'),
                ('hauteur', request.form.get('hauteur'), 'number_integer'),
                ('rayon', request.form.get('rayon'), 'number_integer'),
                ('load_index', request.form.get('load_index'), 'number_integer'),
                ('speed_index', request.form.get('speed_index'), 'single_line_text_field'),
                ('dot', request.form.get('dot'), 'single_line_text_field'),
                ('tread_depth', request.form.get('tread_depth'), 'number_decimal'),
                ('tire_count', request.form.get('tire_count'), 'number_integer'),
                ('commercial_tire', request.form.get('commercial_tire'), 'single_line_text_field'),
                ('tire_provider', request.form.get('tire_provider'), 'single_line_text_field'),
                ('arrival_date', request.form.get('arrival_date'), 'date'),
                ('item_condition', request.form.get('item_condition'), 'single_line_text_field'),
                ('price_difference_to_new', request.form.get('price_difference_to_new'), 'number_integer'),
                ('model', request.form.get('model'), 'single_line_text_field'),
            ]
            
            for key, value, mf_type in metafields_to_add:
                if value:  # Only add if value exists
                    try:
                        metafield = shopify.Metafield()
                        metafield.namespace = 'custom'
                        metafield.key = key
                        metafield.type = mf_type
                        metafield.owner_id = product_id
                        metafield.owner_resource = 'product'
                        
                        # Format value based on type
                        if mf_type == 'number_integer':
                            metafield.value = str(int(float(value)))
                        elif mf_type == 'number_decimal':
                            metafield.value = str(float(value))
                        elif mf_type == 'date':
                            metafield.value = value  # Already in YYYY-MM-DD format
                        else:
                            metafield.value = str(value)
                        
                        result = metafield.save()
                        if result:
                            print(f"✅ Metafield saved: {key} = {metafield.value} ({mf_type})")
                        else:
                            print(f"❌ Metafield FAILED: {key} - {metafield.errors.full_messages()}")
                    except Exception as mf_error:
                        print(f"⚠️ Failed to save metafield {key}: {mf_error}")
            
            # ============================================================
            # ADD PRODUCT TO COLLECTIONS
            # ============================================================
            collection_ids = request.form.getlist('collection_ids')
            collections_added = []
            
            if collection_ids:
                print(f"\n📁 Adding product to {len(collection_ids)} collections...")
                
                for collection_id in collection_ids:
                    if collection_id:  # Skip empty values
                        try:
                            collect = shopify.Collect()
                            collect.product_id = product_id
                            collect.collection_id = int(collection_id)
                            
                            if collect.save():
                                collections_added.append(collection_id)
                                print(f"   ✅ Added to collection: {collection_id}")
                            else:
                                print(f"   ❌ Failed to add to collection {collection_id}: {collect.errors.full_messages()}")
                        except Exception as coll_error:
                            print(f"   ⚠️ Error adding to collection {collection_id}: {coll_error}")
                
                print(f"✅ Product added to {len(collections_added)}/{len(collection_ids)} collections")
            else:
                print("ℹ️ No collections selected")
            # ============================================================
            
            # ============================================================
            # AUTO-PUBLISH TO ALL SALES CHANNELS
            # ============================================================
            publish_result = None
            try:
                print(f"\n📢 Publishing product to all sales channels...")
                publish_result = publish_product_to_all_channels(product_id)
                
                if publish_result['success']:
                    print(f"✅ Product published to all {publish_result['channels_count']} sales channels!")
                else:
                    failed_channels = [r['publication'] for r in publish_result['results'] if not r['success']]
                    print(f"⚠️ Some channels failed: {', '.join(failed_channels)}")
                    
            except Exception as pub_error:
                print(f"⚠️ Publication error: {str(pub_error)}")
                publish_result = {'success': False, 'error': str(pub_error)}
            # ============================================================
            
            # Generate and print label
            # Generate label (always generate PDF, printing disabled)
            label_path = None
            try:
                # Extract tire data for label
                tire_data = extract_tire_data_from_product(product_data, product)
                
                # Get SKU for filename
                sku = product_data.get('sku', str(product_id))
                
                # Generate label with SKU in filename (printing disabled locally)
                label_path = label_printer.generate_and_print(
                    tire_data, 
                    print_enabled=False
                )
                print(f"🏷️  Label created: {label_path}")
                
                # Save label data as JSON for future editing
                if label_path:
                    import json
                    json_path = label_path.replace('.pdf', '.json')
                    with open(json_path, 'w') as f:
                        json.dump(tire_data, f, indent=2)
                
                # Add to remote print queue
                if label_path and REMOTE_PRINTING_ENABLED:
                    try:
                        job_id = create_print_job_with_pdf(label_path, sku, tire_data)
                        print(f"📋 Print job created: {job_id}")
                    except Exception as job_error:
                        print(f"⚠️  Print job creation error: {job_error}")
                
            except Exception as label_error:
                print(f"⚠️  Label generation error: {str(label_error)}")
                # Don't fail the whole request if label generation fails
            
            return jsonify({
                'success': True,
                'message': 'Product created successfully!',
                'product_id': product_id,
                'product_url': f"https://{SHOPIFY_STORE}.myshopify.com/admin/products/{product_id}",
                'label_generated': label_path is not None,
                'label_path': label_path,
                'published': publish_result['success'] if publish_result else False,
                'publish_channels': publish_result.get('channels_count', 0) if publish_result else 0,
                'collections_added': len(collections_added),
                'collections_requested': len(collection_ids) if collection_ids else 0
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
        
        # Generate label (local printing disabled - use remote queue)
        label_path = label_printer.generate_and_print(tire_data, print_enabled=False)
        
        # Add to remote print queue
        job_id = None
        if label_path and REMOTE_PRINTING_ENABLED:
            sku = tire_data.get('sku', str(product_id))
            job_id = create_print_job_with_pdf(label_path, sku, tire_data)
        
        return jsonify({
            'success': True,
            'message': 'Label sent to print queue',
            'label_path': label_path,
            'job_id': job_id
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
    
    # Save label data as JSON for future editing
    if label_path:
        import json
        json_path = label_path.replace('.pdf', '.json')
        with open(json_path, 'w') as f:
            json.dump(test_data, f, indent=2)
    
    return jsonify({
        'success': True,
        'message': 'Test label generated (not printed)',
        'label_path': label_path,
        'note': f'Check {label_path} to verify label design'
    })


# ============================================================
# PUBLICATION ROUTES - View and manage sales channels
# ============================================================

@app.route('/api/publications')
def list_publications():
    """List all available sales channels/publications"""
    # Activate session
    session = shopify.Session(SHOP_URL, "2023-04", SHOPIFY_ACCESS_TOKEN)
    shopify.ShopifyResource.activate_session(session)
    
    try:
        publications = get_all_publications()
        return jsonify({
            'success': True,
            'count': len(publications),
            'publications': publications
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/publish-product/<int:product_id>', methods=['POST'])
def publish_product_route(product_id):
    """Manually publish a product to all sales channels"""
    # Activate session
    session = shopify.Session(SHOP_URL, "2023-04", SHOPIFY_ACCESS_TOKEN)
    shopify.ShopifyResource.activate_session(session)
    
    try:
        result = publish_product_to_all_channels(product_id)
        
        return jsonify({
            'success': result['success'],
            'product_id': product_id,
            'channels_count': result.get('channels_count', 0),
            'results': result['results']
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/product-publications/<int:product_id>')
def get_product_publications(product_id):
    """Check which sales channels a product is published to"""
    # Activate session
    session = shopify.Session(SHOP_URL, "2023-04", SHOPIFY_ACCESS_TOKEN)
    shopify.ShopifyResource.activate_session(session)
    
    try:
        product_gid = f"gid://shopify/Product/{product_id}"
        
        query = """
        query getProductPublications($id: ID!) {
            product(id: $id) {
                id
                title
                resourcePublicationsV2(first: 10) {
                    edges {
                        node {
                            publication {
                                id
                                name
                            }
                            isPublished
                        }
                    }
                }
            }
        }
        """
        
        variables = {"id": product_gid}
        result = shopify.GraphQL().execute(query, variables=variables)
        data = json.loads(result)
        
        if 'errors' in data:
            return jsonify({
                'success': False,
                'error': data['errors']
            }), 400
        
        product_data = data.get('data', {}).get('product', {})
        publications = []
        
        for edge in product_data.get('resourcePublicationsV2', {}).get('edges', []):
            node = edge['node']
            publications.append({
                'id': node['publication']['id'],
                'name': node['publication']['name'],
                'is_published': node.get('isPublished', False)
            })
        
        return jsonify({
            'success': True,
            'product_id': product_id,
            'title': product_data.get('title', ''),
            'publications': publications
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================

# ============================================================
# LABEL MANAGEMENT ROUTES
# ============================================================

@app.route('/api/labels')
def list_labels():
    """List all generated labels"""
    try:
        labels_dir = 'labels'
        if not os.path.exists(labels_dir):
            os.makedirs(labels_dir)
            return jsonify({
                'success': True,
                'labels': [],
                'count': 0
            })
        
        labels = []
        for filename in os.listdir(labels_dir):
            if filename.endswith('.pdf'):
                filepath = os.path.join(labels_dir, filename)
                stat = os.stat(filepath)
                
                # Extract SKU from filename (label_1150.pdf -> 1150)
                sku = filename.replace('label_', '').replace('.pdf', '')
                
                labels.append({
                    'filename': filename,
                    'sku': sku,
                    'size': stat.st_size,
                    'created': stat.st_mtime,
                    'download_url': f'/labels/{filename}',
                    'print_url': f'/api/print-label/{filename}'
                })
        
        # Sort by creation time (newest first)
        labels.sort(key=lambda x: x['created'], reverse=True)
        
        return jsonify({
            'success': True,
            'labels': labels,
            'count': len(labels)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/labels/<filename>')
def download_label(filename):
    """Download/view a label PDF"""
    from flask import send_from_directory
    
    # Security: only allow PDF files from labels directory
    if not filename.endswith('.pdf'):
        return jsonify({'error': 'Invalid file type'}), 400
    
    labels_dir = os.path.join(os.getcwd(), 'labels')
    return send_from_directory(labels_dir, filename, as_attachment=False)


@app.route('/api/label-data/<filename>')
def get_label_data(filename):
    """Get stored label data for editing"""
    try:
        # Security check
        if not filename.endswith('.pdf'):
            return jsonify({
                'success': False,
                'error': 'Invalid file type'
            }), 400
        
        # Try to load label data from JSON file
        json_filename = filename.replace('.pdf', '.json')
        json_path = os.path.join('labels', json_filename)
        
        if os.path.exists(json_path):
            import json
            with open(json_path, 'r') as f:
                label_data = json.load(f)
            return jsonify({
                'success': True,
                'data': label_data
            })
        else:
            # Extract SKU from filename as fallback
            sku = filename.replace('label_', '').replace('.pdf', '')
            return jsonify({
                'success': True,
                'data': {'sku': sku}
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/regenerate-label', methods=['POST'])
def regenerate_label():
    """Regenerate a label with updated data"""
    try:
        data = request.json
        original_filename = data.get('filename', '')
        
        # Security check
        if not original_filename.endswith('.pdf'):
            return jsonify({
                'success': False,
                'error': 'Invalid file type'
            }), 400
        
        # Prepare label data
        label_data = {
            'brand': data.get('brand', ''),
            'model': data.get('model', ''),
            'largeur': data.get('largeur', ''),
            'hauteur': data.get('hauteur', ''),
            'rayon': data.get('rayon', ''),
            'sku': data.get('sku', ''),
            'indice_charge': data.get('indice_charge', ''),
            'indice_vitesse': data.get('indice_vitesse', ''),
            'dot': data.get('dot', ''),
            'profondeur': data.get('profondeur', ''),
            'product_url': f"https://smartpneu.com/products/{data.get('sku', '')}"
        }
        
        # Generate new filename based on SKU
        new_sku = label_data['sku']
        new_filename = f"label_{new_sku}.pdf"
        output_path = os.path.join('labels', new_filename)
        
        # Create labels directory if needed
        os.makedirs('labels', exist_ok=True)
        
        # Generate the new label
        label_printer.create_label(label_data, output_path)
        
        # Save label data as JSON for future editing
        json_path = output_path.replace('.pdf', '.json')
        import json
        with open(json_path, 'w') as f:
            json.dump(label_data, f, indent=2)
        
        # Delete old file if it's different from new one
        old_filepath = os.path.join('labels', original_filename)
        if original_filename != new_filename and os.path.exists(old_filepath):
            os.remove(old_filepath)
            # Also remove old JSON if exists
            old_json = old_filepath.replace('.pdf', '.json')
            if os.path.exists(old_json):
                os.remove(old_json)
        
        print(f"✅ Label regenerated: {new_filename}")
        
        return jsonify({
            'success': True,
            'filename': new_filename,
            'message': 'Label regenerated successfully'
        })
        
    except Exception as e:
        print(f"❌ Label regeneration error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/print-label/<filename>', methods=['POST'])
def print_specific_label(filename):
    """Print a specific label by filename"""
    try:
        # Security check
        if not filename.endswith('.pdf'):
            return jsonify({
                'success': False,
                'error': 'Invalid file type'
            }), 400
        
        filepath = os.path.join('labels', filename)
        
        if not os.path.exists(filepath):
            return jsonify({
                'success': False,
                'error': 'Label not found'
            }), 404
        
        # Print the label
        success = label_printer.print_label(filepath)
        
        return jsonify({
            'success': success,
            'message': f'Label sent to printer: {label_printer.printer_name}' if success else 'Print failed',
            'printer': label_printer.printer_name,
            'filename': filename
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/printer-status')
def printer_status():
    """Get printer configuration and status"""
    import platform
    import subprocess
    
    status = {
        'configured_printer': label_printer.printer_name,
        'auto_print_enabled': AUTO_PRINT_LABELS,
        'black_and_white': label_printer.black_and_white,
        'platform': platform.system(),
        'available_printers': []
    }
    
    try:
        system = platform.system()
        
        if system == "Linux" or system == "Darwin":
            # Get list of printers using lpstat
            result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.startswith('printer'):
                        parts = line.split()
                        if len(parts) >= 2:
                            printer_name = parts[1]
                            is_enabled = 'enabled' in line.lower()
                            status['available_printers'].append({
                                'name': printer_name,
                                'enabled': is_enabled,
                                'is_configured': printer_name == label_printer.printer_name
                            })
            
            # Check if configured printer exists
            status['printer_found'] = any(
                p['name'] == label_printer.printer_name 
                for p in status['available_printers']
            )
            
        elif system == "Windows":
            # Windows printer detection
            try:
                import win32print
                printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
                for printer in printers:
                    printer_name = printer[2]
                    status['available_printers'].append({
                        'name': printer_name,
                        'enabled': True,
                        'is_configured': printer_name == label_printer.printer_name
                    })
                status['printer_found'] = any(
                    p['name'] == label_printer.printer_name 
                    for p in status['available_printers']
                )
            except ImportError:
                status['note'] = 'win32print not available'
                status['printer_found'] = None
        
        status['success'] = True
        
    except Exception as e:
        status['success'] = False
        status['error'] = str(e)
    
    return jsonify(status)


@app.route('/api/set-printer', methods=['POST'])
def set_printer():
    """Change the configured printer"""
    global label_printer
    
    data = request.get_json()
    new_printer = data.get('printer_name')
    
    if not new_printer:
        return jsonify({
            'success': False,
            'error': 'No printer name provided'
        }), 400
    
    old_printer = label_printer.printer_name
    label_printer.printer_name = new_printer
    
    return jsonify({
        'success': True,
        'old_printer': old_printer,
        'new_printer': new_printer,
        'message': f'Printer changed from {old_printer} to {new_printer}'
    })


@app.route('/api/set-color-mode', methods=['POST'])
def set_color_mode():
    """Toggle between black & white and color printing"""
    global label_printer
    
    data = request.get_json()
    black_and_white = data.get('black_and_white', True)
    
    label_printer.black_and_white = black_and_white
    mode = "Black & White" if black_and_white else "Color"
    
    return jsonify({
        'success': True,
        'black_and_white': black_and_white,
        'message': f'Print mode changed to: {mode}'
    })


@app.route('/api/generate-test-label', methods=['POST'])
def generate_test_label():
    """Generate a test label with current color mode settings"""
    try:
        data = request.get_json() or {}
        send_to_printer = data.get('send_to_printer', False)
        
        test_data = {
            'brand': 'TEST',
            'model': 'Color Mode Test',
            'largeur': '225',
            'hauteur': '45',
            'rayon': '17',
            'indice_charge': '94',
            'indice_vitesse': 'Y',
            'dot': '0125',
            'profondeur': '8mm',
            'sku': f'TEST-{"BW" if label_printer.black_and_white else "COLOR"}',
            'product_url': 'https://smartpneu.com/test'
        }
        
        # Generate without local printing
        pdf_path = label_printer.generate_and_print(test_data, print_enabled=False)
        mode = "B&W" if label_printer.black_and_white else "Color"
        
        # Save label data as JSON for future editing
        if pdf_path:
            import json
            json_path = pdf_path.replace('.pdf', '.json')
            with open(json_path, 'w') as f:
                json.dump(test_data, f, indent=2)
        
        # Optionally add to print queue
        job_id = None
        if send_to_printer and REMOTE_PRINTING_ENABLED:
            job_id = create_print_job_with_pdf(pdf_path, test_data['sku'], test_data)
        
        return jsonify({
            'success': True,
            'message': f'Test label generated in {mode} mode',
            'label_path': pdf_path,
            'mode': mode,
            'filename': os.path.basename(pdf_path),
            'job_id': job_id,
            'sent_to_printer': job_id is not None
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/delete-label/<filename>', methods=['DELETE'])
def delete_label(filename):
    """Delete a label PDF and its associated JSON data"""
    try:
        if not filename.endswith('.pdf'):
            return jsonify({
                'success': False,
                'error': 'Invalid file type'
            }), 400
        
        filepath = os.path.join('labels', filename)
        
        if not os.path.exists(filepath):
            return jsonify({
                'success': False,
                'error': 'Label not found'
            }), 404
        
        os.remove(filepath)
        
        # Also remove JSON data file if exists
        json_path = filepath.replace('.pdf', '.json')
        if os.path.exists(json_path):
            os.remove(json_path)
        
        return jsonify({
            'success': True,
            'message': f'Label {filename} deleted'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================
# PRINT JOB QUEUE API (for remote print agent)
# ============================================================

# Import storage module
try:
    from storage import (
        create_print_job_with_pdf, get_pending_jobs,
        complete_job, get_all_jobs, get_job, get_pending_count
    )
    REMOTE_PRINTING_ENABLED = True
except ImportError:
    REMOTE_PRINTING_ENABLED = False
    print("⚠️  Storage module not available - remote printing disabled")

# Optional API key for print agent authentication
PRINT_AGENT_API_KEY = os.getenv('PRINT_AGENT_API_KEY', '')


def verify_api_key():
    """Verify API key if configured"""
    if not PRINT_AGENT_API_KEY:
        return True  # No key configured, allow all
    
    provided_key = request.headers.get('X-API-Key', '')
    return provided_key == PRINT_AGENT_API_KEY


@app.route('/api/print-jobs', methods=['GET'])
def list_print_jobs():
    """Get pending print jobs with embedded PDF data (for print agent)"""
    if not verify_api_key():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        pending = get_pending_jobs(include_pdf=True)
        return jsonify({
            'jobs': pending,
            'count': len(pending)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/print-jobs/<job_id>/complete', methods=['POST'])
def mark_print_job_complete(job_id):
    """Mark a print job as complete (called by print agent)"""
    if not verify_api_key():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json() or {}
        success = data.get('success', True)
        message = data.get('message', '')
        printer = data.get('printer', '')
        
        result = complete_job(job_id, success, message, printer)
        
        if result:
            return jsonify({
                'success': True,
                'job_id': job_id,
                'status': 'complete' if success else 'failed'
            })
        else:
            return jsonify({'error': 'Job not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/print-jobs/all', methods=['GET'])
def list_all_print_jobs():
    """Get all print jobs without PDF data (for admin/debugging)"""
    if not verify_api_key():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        all_jobs = get_all_jobs(limit=100)
        return jsonify({
            'jobs': all_jobs,
            'count': len(all_jobs)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/print-jobs/status', methods=['GET'])
def print_jobs_status():
    """Get print queue status"""
    try:
        return jsonify({
            'pending_count': get_pending_count(),
            'remote_printing_enabled': REMOTE_PRINTING_ENABLED
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================

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