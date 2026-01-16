# Label Printing Integration Guide

This guide explains how to add automatic label printing to your SmartPneu Product Manager.

## What This Adds

✅ Automatic label generation when products are created
✅ Professional 70mm x 170mm tire labels matching your design
✅ QR codes linking to product pages
✅ Direct printing to HP Color LaserJet MFP M179fnw
✅ PDF backup of all labels in `labels/` folder
✅ Manual reprint endpoint for existing products
✅ Test endpoint to verify label design

## Installation Steps

### 1. Add New Files to Your Repository

Add these three new files to your project:

```bash
# In your project root directory:
git pull  # Make sure you're up to date

# Add the new files:
# - label_printer.py (new file)
# - app_updated.py (will replace app.py)
# - requirements_updated.txt (will replace requirements.txt)
```

Copy the contents from:
- `label_printer.py` → Your repo's root directory
- `app_updated.py` → Backup your `app.py`, then replace with this
- `requirements_updated.txt` → Replace your `requirements.txt`

### 2. Update Environment Variables

Update your `.env` file with printer settings:

```bash
# Add these lines to your .env file:
PRINTER_NAME=HP_Color_LaserJet_MFP_M179fnw
AUTO_PRINT_LABELS=true
```

### 3. Install New Dependencies

```bash
pip install -r requirements.txt
```

**For Windows only:**
```bash
pip install pywin32
```

### 4. Configure Your Printer

#### Windows:
1. Open Control Panel → Devices and Printers
2. Find your HP Color LaserJet MFP M179fnw
3. Copy the exact printer name
4. Update `PRINTER_NAME` in `.env` with this exact name

#### Linux/Mac:
```bash
# List available printers
lpstat -p -d

# Make sure your printer is set as default
lpoptions -d HP_Color_LaserJet_MFP_M179fnw
```

### 5. Test Label Generation (Without Printing)

Before enabling automatic printing, test the label design:

```bash
# Start your Flask app
python app.py

# In another terminal or browser, call the test endpoint:
curl http://localhost:5000/test-label

# Or open in browser:
# http://localhost:5000/test-label
```

This will create a test label at `labels/label_TEST-001.pdf`. Open this file to verify the design looks correct.

### 6. Update Your Product Creation Form

Your existing form should already capture tire specifications. Make sure your HTML form includes these fields:

- `largeur` (Width)
- `hauteur` (Height)  
- `rayon` (Radius)
- `indice_charge` (Load index)
- `indice_vitesse` (Speed index)
- `dot` (DOT number)
- `profondeur` (Tread depth)
- `sku` (SKU/Reference)

These are automatically extracted and used for label generation.

### 7. Enable Automatic Printing

Once you've verified the test label looks good:

```bash
# In your .env file, make sure this is set:
AUTO_PRINT_LABELS=true
```

Restart your Flask app.

## How It Works

### Product Creation Flow

1. **User submits product form** → Your existing form
2. **Product created in Shopify** → Existing functionality
3. **Metafields added** → Tire specifications saved
4. **Label generated** → New: 70mm x 170mm PDF created
5. **Label printed** → New: Sent directly to HP printer
6. **PDF saved** → New: Backup in `labels/` folder

### File Structure

```
smartpneu-product-manager/
├── app.py                    # Updated with label printing
├── label_printer.py          # New: Label generation module
├── requirements.txt          # Updated with new dependencies
├── .env                      # Updated with printer config
├── labels/                   # New: Generated label PDFs
│   ├── label_SKU001.pdf
│   ├── label_SKU002.pdf
│   └── ...
└── templates/
    └── index.html            # Your existing form
```

## API Endpoints

### Existing Endpoints
- `GET /` - Product creation form
- `POST /create-product` - Create product (now with label printing)

### New Endpoints
- `GET /test-label` - Generate test label without printing
- `POST /print-label/<product_id>` - Reprint label for existing product
- `GET /health` - Check system status and printer connection

## Usage Examples

### 1. Create Product with Label (Automatic)

When you create a product through the form at `http://localhost:5000/`, the label will automatically:
1. Generate as PDF
2. Print to your HP printer
3. Save to `labels/` folder

### 2. Reprint Label for Existing Product

```bash
# Via API
curl -X POST http://localhost:5000/print-label/PRODUCT_ID

# Or add a "Reprint Label" button in your UI
```

### 3. Generate Label Without Printing

Set `AUTO_PRINT_LABELS=false` in `.env` to only generate PDFs without printing.

## Troubleshooting

### Label Not Printing

**Check printer name:**
```bash
# Windows
# Open Control Panel → Devices and Printers and verify exact name

# Linux/Mac
lpstat -p
```

**Check printer connection:**
- Make sure printer is online
- Try printing a test page from system settings
- Check printer queue for errors

### Label Design Issues

**Test label generation:**
```bash
curl http://localhost:5000/test-label
```

Check `labels/label_TEST-001.pdf` to see the output.

**Adjust label layout:**
Edit `label_printer.py` and modify the `create_label()` method:
- Font sizes: Change `c.setFont("Helvetica", SIZE)`
- Positions: Adjust `y_position` and `line_height`
- Colors: Modify `HexColor()` values

### Missing Data on Labels

Make sure your product form includes all tire specification fields:

```html
<input type="text" name="largeur" placeholder="Width (e.g., 225)">
<input type="text" name="hauteur" placeholder="Height (e.g., 45)">
<input type="text" name="rayon" placeholder="Radius (e.g., 17)">
<!-- etc -->
```

### Printer Permission Errors (Linux)

```bash
# Add your user to the lp group
sudo usermod -a -G lp $USER

# Restart your session
```

## Customization

### Change Label Size

Edit `label_printer.py`:

```python
def __init__(self, printer_name="..."):
    self.width = 70 * mm   # Change width
    self.height = 170 * mm # Change height
```

### Change Printer

Update `.env`:

```bash
PRINTER_NAME=Your_Printer_Name_Here
```

### Disable Auto-Printing

Update `.env`:

```bash
AUTO_PRINT_LABELS=false
```

Labels will still be generated and saved to `labels/` folder.

### Custom Label Design

Edit the `create_label()` method in `label_printer.py`:
- Colors: `HexColor("#CC0000")` for red, `HexColor("#0099CC")` for blue
- Fonts: `c.setFont("Helvetica-Bold", size)`
- Layout: Adjust `y_position` and spacing

## Production Deployment

When deploying to Heroku/AWS:

1. **Disable auto-printing** (printers not available on cloud servers):
```bash
AUTO_PRINT_LABELS=false
```

2. **Download labels** via admin interface or API
3. **Print manually** from downloaded PDFs

Or:

1. **Keep auto-printing enabled** on local development
2. **Run the app locally** on a computer connected to your printer
3. **Use webhooks** to notify your local instance when products are created

## Testing Checklist

Before going live:

- [ ] Test label generation: `curl http://localhost:5000/test-label`
- [ ] Verify label design in generated PDF
- [ ] Test manual print: Create product and check if label prints
- [ ] Check `labels/` folder for PDF backups
- [ ] Verify all tire specifications appear correctly
- [ ] Test QR code by scanning with phone
- [ ] Confirm printer receives jobs

## Need Help?

Common issues:
1. **Printer not found**: Double-check `PRINTER_NAME` in `.env`
2. **Module not found**: Run `pip install -r requirements.txt`
3. **Label design off**: Check label dimensions match your sticker paper
4. **No data on label**: Verify form field names match expected keys

## Git Integration

After adding these files:

```bash
git add label_printer.py
git add app.py
git add requirements.txt
git add .env.example
git add labels/.gitkeep  # Keep labels folder in git
git commit -m "Add automatic label printing functionality"
git push
```

Don't forget to add `labels/*.pdf` to `.gitignore` so PDFs aren't committed:

```bash
echo "labels/*.pdf" >> .gitignore
```
