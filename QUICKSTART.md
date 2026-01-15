# Quick Start Guide

## Installation & Setup

1. **Install dependencies:**
   ```bash
   cd /Users/mohan.as1/Documents/payload-scaler
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   python3 app.py
   ```
   Or use the run script:
   ```bash
   ./run.sh
   ```

3. **Open in browser:**
   ```
   http://localhost:5001
   ```

## Example Usage

### Step 1: Input Payload
Paste a JSON payload like this:
```json
{
  "users": [
    {
      "id": 1,
      "name": "John Doe",
      "email": "john@example.com",
      "orders": [
        {
          "id": 1,
          "total": 100.50,
          "items": [
            {"product": "Widget", "qty": 2}
          ]
        }
      ]
    }
  ],
  "metadata": {
    "version": "1.0"
  }
}
```

### Step 2: Analyze
Click "Analyze Payload" button. The system will identify:
- `users` - array with 1 item
- `users[0].orders` - nested array with 1 item  
- `users[0].orders[0].items` - nested array with 1 item

### Step 3: Set Counts
For each entity found, set your desired count:
- `users`: 10 (will create 10 users)
- `users.orders`: 5 (will create 5 orders per user)
- `users.orders.items`: 3 (will create 3 items per order)

### Step 4: Generate
Click "Generate Scaled Payload" to create the new payload with:
- 10 users
- Each user has 5 orders
- Each order has 3 items

### Step 5: Export
- Click "Copy to Clipboard" to copy the JSON
- Click "Download JSON" to save as a file

## Features

✅ **Automatic Entity Detection**: Finds all arrays in your payload
✅ **Nested Entity Support**: Handles deeply nested structures
✅ **Visual Preview**: See sample structure for each entity
✅ **Real-time Generation**: Instant payload generation
✅ **Easy Export**: Copy or download generated payloads

## Tips

- Use Ctrl+Enter in the payload input to quickly analyze
- Empty arrays are also detected as scalable entities
- The first item in each array is used as the template for scaling
- Nested entities are scaled recursively

