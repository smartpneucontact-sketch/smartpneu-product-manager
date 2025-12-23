# Automatic Price Difference Calculation

## How It Works

The **price in JSON** is the **new tire reference price** (not the selling price).

When you enter the **used tire price**, it automatically calculates the **percentage discount**.

## Example

### JSON Data:
```json
{
    "name": "Pilot Sport 4",
    "type": "Ete",
    "speed_index": "Y",
    "load_index": "91",
    "price": "150.00",  // ← New tire reference price
    ...
}
```

### User Workflow:

1. **Select model:** Pilot Sport 4
   - Helper text appears: *"New tire price: 150€ - Enter used tire price"*

2. **User enters used price:** 105€
   - System calculates: `((150 - 105) / 150) × 100 = 30%`
   - **Price Difference to New (%)** field auto-fills: `30`

3. **User submits** → Product created with:
   - Price: 105€
   - Price difference metafield: 30%

## Calculation Formula

```
Price Difference % = ((New Price - Used Price) / New Price) × 100
```

**Examples:**

| New Price | Used Price | Calculation | Difference % |
|-----------|------------|-------------|--------------|
| 150€ | 105€ | ((150-105)/150)×100 | 30% |
| 200€ | 140€ | ((200-140)/200)×100 | 30% |
| 120€ | 90€ | ((120-90)/120)×100 | 25% |
| 180€ | 99€ | ((180-99)/180)×100 | 45% |

## Visual Flow

```
1. Select Model
   ↓
   Helper text shows: "New tire price: 150€ - Enter used tire price"
   
2. User types in price field: 105
   ↓
   Auto-calculation happens in real-time
   ↓
   "Price Difference to New (%)" field updates to: 30
   
3. User can:
   - Adjust the used price → percentage recalculates automatically
   - Manually override the percentage if needed
   - Submit the form
```

## Console Output

When you enter a price, you'll see:
```
Calculating: New price: 150€, Used price: 105€, Difference: 30%
```

## Features

✅ **Real-time calculation** - Updates as you type
✅ **Visual reference** - Shows new tire price in helper text
✅ **Automatic rounding** - Rounds to nearest whole percent
✅ **Manual override** - User can change percentage if needed
✅ **No field population** - Price field stays empty until user enters value

## Setting Up JSON Prices

In `brands_models.json`, set the `price` to the **new tire market price**:

```json
{
    "name": "Michelin",
    "models": [
        {
            "name": "Pilot Sport 4",
            "price": "150.00"  // ← What this tire costs NEW
        },
        {
            "name": "Pilot Sport 5",
            "price": "165.00"  // ← What this tire costs NEW
        }
    ]
}
```

## Typical Used Tire Pricing

Generally, used tires sell for 20-50% less than new, depending on condition:

| Condition | Tread Depth | Typical Discount |
|-----------|-------------|------------------|
| Excellent | 7-8mm | 20-30% |
| Good | 5-7mm | 30-40% |
| Fair | 3-5mm | 40-50% |
| Poor | <3mm | 50%+ |

**Example workflow:**
1. New Michelin Pilot Sport 4: **150€**
2. Used tire with 6mm tread (Good condition)
3. Price at **35% discount** = 150€ × 0.65 = **97.50€**
4. System auto-calculates and shows **35%** in difference field

## Installation

1. **Replace file:**
   - `templates/index.html` with `index_with_price_calc.html`

2. **Restart Flask**

3. **Test:**
   - Select a tire model
   - Check helper text shows new price
   - Enter a used price
   - Watch percentage auto-calculate!

## Troubleshooting

**Percentage not calculating?**
1. Check browser console (F12) for errors
2. Make sure price in JSON is a number, not string with currency
3. Verify you entered a valid number in price field

**Wrong percentage showing?**
1. Check the formula is correct
2. Verify new price in JSON is accurate
3. Check console to see what values are being used

**Helper text not updating?**
1. Make sure model was selected
2. Check JSON has "price" field for that model
3. Restart Flask if JSON was recently changed

## Benefits

✅ **Faster pricing** - No manual calculation needed
✅ **Consistent** - Same formula used every time
✅ **Transparent** - Shows reference price to user
✅ **Flexible** - User can still override if needed
✅ **Professional** - Accurate discount percentages for customers

Perfect for quickly pricing used tires based on condition and market value! 💰
