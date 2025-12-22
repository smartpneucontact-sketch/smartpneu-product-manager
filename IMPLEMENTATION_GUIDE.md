# SmartPneu Product Manager - Auto-Population Update

## Changes Made

I've updated your SmartPneu Product Manager to automatically populate tire information when a model is selected. Here's what changed:

### 1. **brands_models.json** - New Structure

The JSON file now includes detailed information for each tire model:

```json
{
    "brands": [
        {
            "name": "Michelin",
            "models": [
                {
                    "name": "Pilot Sport 4",
                    "type": "Ete",
                    "speed_index": "Y",
                    "load_index": "91",
                    "price": "150.00"
                }
            ]
        }
    ]
}
```

**New Fields:**
- `type`: Tire season type - "Ete", "Hiver", or "4 saisons"
- `speed_index`: Speed rating (Q, R, S, T, U, H, V, ZR, W, Y)
- `load_index`: Load capacity index (number, e.g., "91")
- `price`: Default price for this model

### 2. **app.py** - API Updates

#### Updated `load_brands_models()` function
- Now handles the new JSON structure
- Maintains backward compatibility with old format
- Converts the new format to a dictionary for easy access

#### New API endpoint: `/api/model-details/<brand>/<model>`
- Returns complete details for a specific tire model
- Used by the frontend to auto-populate fields

#### Updated `/api/get-models/<brand>` endpoint
- Now extracts just model names from the new structure
- Maintains compatibility with existing dropdown functionality

### 3. **index.html** - Auto-Population JavaScript

Added JavaScript that automatically populates form fields when a tire model is selected:

**Auto-populated fields:**
1. **Product Type** - Sets to "Pneu d'été", "Pneu hiver", or "Pneus 4 saisons" based on tire type
2. **Speed Index** - Selects the correct speed rating
3. **Load Index** - Fills in the load capacity number
4. **Price** - Sets the default price

**User can still override** any auto-populated value manually.

## How It Works

### User Flow:
1. User selects a **Brand** (e.g., "Michelin")
2. Models dropdown populates with available models
3. User selects a **Model** (e.g., "Pilot Sport 4")
4. **Automatically happens:**
   - Product Type → "Pneu d'été"
   - Speed Index → "Y"
   - Load Index → "91"
   - Price → "150.00"
5. User can manually adjust any field if needed
6. User completes other fields (Largeur, Hauteur, Rayon, etc.)
7. Submit form to create product

## Installation

1. **Backup your current files** (recommended!)

2. **Replace these files:**
   - `brands_models.json` - Replace with the new version
   - `app.py` - Replace with updated version
   - `templates/index.html` - Replace with updated version

3. **Update your data:**
   - Edit `brands_models.json` to add your tire models with correct information
   - Fill in accurate prices, speed indices, and load indices for each model

4. **Restart your Flask app:**
   ```bash
   python app.py
   ```

## Adding New Tire Models

To add a new tire model, edit `brands_models.json`:

```json
{
    "name": "Your Model Name",
    "type": "Ete",           // or "Hiver" or "4 saisons"
    "speed_index": "V",      // Speed rating letter
    "load_index": "94",      // Load capacity number
    "price": "145.00"        // Price in euros
}
```

### Speed Index Reference:
- Q (160 km/h)
- R (170 km/h)
- S (180 km/h)
- T (190 km/h)
- U (200 km/h)
- H (210 km/h)
- V (240 km/h)
- ZR (240+ km/h)
- W (270 km/h)
- Y (300 km/h)

### Load Index Reference:
Common values range from 60 to 130, representing load capacity in kg.
Examples: 88, 91, 94, 95, 98, 100, etc.

## Benefits

✅ **Faster product creation** - No need to manually look up specifications
✅ **Fewer errors** - Consistent data from centralized source
✅ **Easy maintenance** - Update prices and specs in one place
✅ **Still flexible** - Users can override any auto-filled value
✅ **Backward compatible** - Works with old JSON format if needed

## Testing

After installation, test the flow:

1. Open the application in your browser
2. Select "Michelin" from Brand dropdown
3. Select "Pilot Sport 4" from Model dropdown
4. Verify these fields auto-populate:
   - Product Type: "Pneu d'été"
   - Speed Index: "Y"
   - Load Index: "91"
   - Price: "150.00"
5. Try modifying an auto-populated field manually
6. Complete the form and create a test product

## Troubleshooting

**Fields not auto-populating?**
- Check browser console for JavaScript errors (F12)
- Verify `brands_models.json` format is correct
- Ensure Flask app restarted after file changes

**Wrong values showing?**
- Double-check data in `brands_models.json`
- Verify spelling of tire types: "Ete", "Hiver", "4 saisons"

**Models not showing in dropdown?**
- Ensure brand name matches exactly in JSON
- Check JSON syntax (commas, brackets, quotes)

## Questions?

If you need help or want to add more features, let me know!
