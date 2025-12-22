# Tire Type Collection Auto-Assignment Update

## What's New

Now the tire type also auto-selects a collection:

| Tire Type in JSON | Auto-Selected Collection |
|-------------------|-------------------------|
| `"type": "Ete"` | "ÉTÉ" |
| `"type": "Hiver"` | "HIVER" |
| `"type": "4 saisons"` | "4 SAISONS" |

## Example

```json
{
    "name": "CrossClimate 2",
    "type": "4 saisons",      // ← Auto-adds to "4 SAISONS" collection
    "speed_index": "V",
    "load_index": "94",
    "price": "175.00",
    "3pmsf": true,            // ← Auto-adds to "3PMSF" collection
    "runflat": false,
    "protection_jante": false,
    "renforce": false
}
```

**When user selects this model, collections auto-appear:**
- `[4 SAISONS] [×]`
- `[3PMSF] [×]`

## Setup

### 1. Create Collections in Shopify

Make sure you have these collections:
- **ÉTÉ** (for summer tires)
- **HIVER** (for winter tires)
- **4 SAISONS** (for all-season tires)
- 3PMSF
- RUNFLAT
- PROTECTION JANTE
- Renforcé

### 2. Replace File

Replace `templates/index.html` with `index_with_type_collections.html`

### 3. Restart & Test

1. Restart Flask
2. Hard refresh browser (Ctrl+Shift+R)
3. Select a tire model
4. Watch both type collection AND feature collections auto-appear!

## Complete Auto-Assignment Logic

The system now auto-adds collections based on:

1. **Tire Type** → ÉTÉ / HIVER / 4 SAISONS
2. **3PMSF** → 3PMSF collection
3. **RunFlat** → RUNFLAT collection
4. **Protection Jante** → PROTECTION JANTE collection
5. **Renforcé** → Renforcé collection

## Example Scenarios

### Summer Performance Tire
```json
{
    "type": "Ete",
    "3pmsf": false,
    "runflat": false,
    "protection_jante": true,
    "renforce": false
}
```
**Auto-selected collections:** ÉTÉ, PROTECTION JANTE

### All-Season Tire
```json
{
    "type": "4 saisons",
    "3pmsf": true,
    "runflat": false,
    "protection_jante": false,
    "renforce": false
}
```
**Auto-selected collections:** 4 SAISONS, 3PMSF

### Winter Run-Flat
```json
{
    "type": "Hiver",
    "3pmsf": true,
    "runflat": true,
    "protection_jante": true,
    "renforce": false
}
```
**Auto-selected collections:** HIVER, 3PMSF, RUNFLAT, PROTECTION JANTE

That's it! Now collections are fully automated based on tire specifications! 🎯
