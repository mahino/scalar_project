# API Payload Scaler

A web application that allows you to analyze API payloads, identify scalable entities (arrays), and generate new payloads with custom entity counts.

## Features

- 📊 **Payload Analysis**: Automatically identifies all arrays/entities in your JSON payload
- 🔢 **Entity Scaling**: Set custom counts for each entity
- 🎯 **Payload Generation**: Generate new payloads with scaled entities
- 📋 **Copy & Download**: Easy export of generated payloads
- 🎨 **Modern UI**: Clean, responsive interface with Bootstrap 5

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

3. Open your browser and navigate to:
```
http://localhost:5001
```

## Usage

1. **Input Payload**: Paste your JSON payload in the text area
2. **Analyze**: Click "Analyze Payload" to identify all entities
3. **Set Counts**: Adjust the count for each entity found
4. **Generate**: Click "Generate Scaled Payload" to create the new payload
5. **Export**: Copy to clipboard or download as JSON file

## Example Payload

```json
{
  "users": [
    {"id": 1, "name": "John", "email": "john@example.com"}
  ],
  "orders": [
    {"id": 1, "total": 100, "items": [{"product": "A", "qty": 2}]}
  ]
}
```

After analysis, you can scale:
- `users` array: Set count to 10 to generate 10 user objects
- `orders` array: Set count to 5 to generate 5 order objects
- `orders[0].items` array: Set count to 3 to generate 3 item objects per order

## How It Works

1. The application recursively traverses your JSON payload
2. Identifies all arrays (potential entities to scale)
3. Shows the current count and sample structure for each entity
4. When generating, duplicates the first item in each array N times based on your specified count

## License

MIT

