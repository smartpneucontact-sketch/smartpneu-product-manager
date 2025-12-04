# SmartPneu Product Manager

A Flask web application to add products to your SmartPneu Shopify store.

## Features

- ✅ Create products with title, description, price, and more
- ✅ Add tire specifications (Largeur, Hauteur, Rayon) as metafields
- ✅ Upload multiple product images
- ✅ Assign products to collections
- ✅ Set inventory quantities
- ✅ Connection status indicator

## Setup

### 1. Install Python dependencies

```bash
cd shopify-product-manager
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy the example environment file and edit it:

```bash
cp .env.example .env
```

Open `.env` and add your Shopify credentials:

```
SHOPIFY_STORE=smartpneu
SHOPIFY_ACCESS_TOKEN=shpat_your_token_here
SECRET_KEY=generate-a-random-string
```

### 3. Run the application

```bash
python app.py
```

### 4. Open in browser

Go to: http://localhost:5000

## Usage

1. Fill in the product details in the form
2. Add tire specifications (Largeur, Hauteur, Rayon)
3. Upload product images (optional)
4. Select a collection (optional)
5. Click "Create Product"

The product will be created in your Shopify store!

## Metafields

The app creates these metafields under the `custom` namespace:

| Metafield | Type | Example |
|-----------|------|---------|
| `custom.largeur` | Number | 225 |
| `custom.hauteur` | Number | 45 |
| `custom.rayon` | Text | R17 |

## Troubleshooting

### Connection failed
- Check your access token is correct
- Make sure the token has `read_products` and `write_products` scopes
- Verify your store name is correct (just the name, not the full URL)

### Product not appearing
- Check if the product was created as "Draft" - change status to "Active"
- Refresh your Shopify admin

### Images not uploading
- Make sure images are under 16MB
- Supported formats: PNG, JPG, GIF, WebP
