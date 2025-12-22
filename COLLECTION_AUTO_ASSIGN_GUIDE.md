# Auto-Assign Collections Based on Tire Features

## How It Works (Simple!)

When you select a tire model, if any boolean feature is `true` in the JSON, the product is **automatically added to the corresponding collection**.

### Example:

```json
{
    "name": "CrossClimate 2",
    "type": "4 saisons",
    "speed_index": "V",
    "load_index": "94",
    "price": "175.00",
    "3pmsf": true,           // ← Auto-adds to "3PMSF" collection
    "runflat": false,
    "protection_jante": false,
    "renforce": false
}
```

When user selects "CrossClimate 2":
- ✅ Automatically adds to "3PMSF" collection (because it's `true`)
- User can still add/remove collections manually

## Collection Name Mapping

The system looks for these exact collection names in your Shopify store:

| Boolean in JSON | Collection Name |
|-----------------|-----------------|
| `"3pmsf": true` | "3PMSF" |
| `"runflat": true` | "RUNFLAT" |
| `"protection_jante": true` | "PROTECTION JANTE" |
| `"renforce": true` | "Renforcé" |

**Important:** Collection names are case-insensitive (it will match "3pmsf", "3PMSF", "3PmSf", etc.)

## Setup Requirements

### 1. Create Collections in Shopify

Make sure you have these collections created in your Shopify store:
- 3PMSF
- RUNFLAT
- PROTECTION JANTE
- Renforcé

**How to create:**
1. Shopify Admin → Products → Collections
2. Click "Create collection"
3. Name it exactly as shown above
4. Save

### 2. Update brands_models.json

Use the JSON structure with boolean fields:

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
                    "price": "150.00",
                    "3pmsf": false,
                    "runflat": false,
                    "protection_jante": true,
                    "renforce": false
                }
            ]
        }
    ]
}
```

### 3. Replace Files

- `brands_models.json` → Use version with boolean fields
- `templates/index.html` → Use `index_collection_auto.html`
- `app.py` → Use `app_collection_auto.py`

### 4. Restart & Test

1. Restart Flask
2. Hard refresh browser (Ctrl+Shift+R)
3. Select a tire model with `"3pmsf": true`
4. Watch the collection tags appear automatically!

## User Flow

```
1. User selects: Continental SportContact 7
   ↓
2. System checks JSON:
   "3pmsf": false         → No action
   "runflat": true        → Auto-adds to "RUNFLAT" collection
   "protection_jante": true → Auto-adds to "PROTECTION JANTE" collection
   "renforce": false      → No action
   ↓
3. Collection tags appear:
   [RUNFLAT] [×]
   [PROTECTION JANTE] [×]
   ↓
4. User can:
   - Remove auto-added collections (click ×)
   - Add more collections manually
   - Submit form
```

## Console Output

When you select a model, you'll see in the browser console (F12):

```
Feature 3pmsf is true, looking for collection: 3PMSF
Auto-adding to collection: 3PMSF (ID: 123456789)
Feature runflat is true, looking for collection: RUNFLAT
Auto-adding to collection: RUNFLAT (ID: 987654321)
```

## What if Collection Doesn't Exist?

If a collection isn't found in your Shopify store:
- The feature is **silently skipped** (no error)
- You'll see a console log but no collection tag appears
- Product creation continues normally

**Solution:** Create the missing collection in Shopify

## Customizing Collection Names

If you want different collection names, edit the mapping in `templates/index.html`:

Find this section:
```javascript
const featureCollections = {
    '3pmsf': '3PMSF',              // ← Change "3PMSF" to your collection name
    'runflat': 'RUNFLAT',          // ← Change "RUNFLAT" to your collection name
    'protection_jante': 'PROTECTION JANTE',
    'renforce': 'Renforcé'
};
```

Change the values to match your Shopify collection names exactly.

## Example Configurations

**All-Season Tire:**
```json
{
    "name": "CrossClimate 2",
    "3pmsf": true,           → Adds to "3PMSF"
    "runflat": false,
    "protection_jante": false,
    "renforce": false
}
```
**Result:** Product in "3PMSF" collection

**High-Performance Run-Flat:**
```json
{
    "name": "Pilot Sport 4 S",
    "3pmsf": false,
    "runflat": true,         → Adds to "RUNFLAT"
    "protection_jante": true, → Adds to "PROTECTION JANTE"
    "renforce": false
}
```
**Result:** Product in "RUNFLAT" and "PROTECTION JANTE" collections

**Commercial Reinforced Tire:**
```json
{
    "name": "Agilis CrossClimate",
    "3pmsf": true,           → Adds to "3PMSF"
    "runflat": false,
    "protection_jante": false,
    "renforce": true         → Adds to "Renforcé"
}
```
**Result:** Product in "3PMSF" and "Renforcé" collections

## Benefits

✅ **Fast** - Collections auto-assign based on tire specs
✅ **Consistent** - No manual errors in collection assignment
✅ **Flexible** - User can still add/remove collections manually
✅ **Simple** - Just set boolean to `true` in JSON
✅ **Clean** - No checkboxes or extra form fields needed

## Troubleshooting

**Collections not auto-adding?**
1. Check collection names match exactly (case-insensitive but spelling must match)
2. Verify collections exist in Shopify
3. Check browser console for errors
4. Verify JSON booleans are `true` not `"true"` (no quotes)

**Wrong collections being added?**
1. Check the JSON file has correct boolean values
2. Restart Flask after changing JSON
3. Hard refresh browser

That's it! Simple and automatic! 🚀
