# Semantic Engine API

The Semantic Engine API is a powerful text processing service that provides advanced natural language processing capabilities. It serves as the backend for the Eva Discord bot and can also be used as a standalone service.

## Features

- **Text Summarization**: Generate concise summaries with titles from long text
- **Atomic Idea Extraction**: Extract key atomic ideas with importance ratings
- **Custom Extraction**: Create custom extractions with user-defined prompts
- **REST API**: Programmatic access to all text processing features

## API Endpoints

### Health Check
```
GET /api/health
```
Response:
```json
{
  "status": "healthy"
}
```

### Text Summarization
```
POST /api/summarize
```
Request body:
```json
{
  "text": "Long text to summarize..."
}
```
Response:
```json
{
  "title": "Generated title",
  "summary": "Generated summary..."
}
```

### Atomic Idea Extraction
```
POST /api/extract_ideas
```
Request body:
```json
{
  "text": "Text to extract ideas from..."
}
```
Response:
```json
{
  "ideas": [
    {
      "idea": "Extracted idea",
      "importance": 0.85
    }
  ]
}
```

### Custom Extraction
```
POST /api/custom_extraction
```
Request body:
```json
{
  "text": "Text to process...",
  "prompt": "Custom extraction prompt...",
  "separator": ":::",
  "parse_score": true,
  "temperature": 0.7
}
```
Response:
```json
{
  "results": [
    {
      "content": "Extracted content",
      "score": 0.92
    }
  ]
}
```

## Running the API

### Development
```bash
python run.py
```

### Production
```bash
gunicorn -w 4 -b 0.0.0.0:5000 'semantic_engine_api.api:create_app()'
```

## Environment Variables

- `ANTHROPIC_API_KEY`: Your Anthropic API key
- `PORT`: Port to run the API on (default: 5000)

## Development

The API is built with Flask and uses the following structure:
```
semantic_engine_api/
├── services/        # Text processing services
│   ├── summarization.py
│   ├── extraction.py
│   ├── atomic_ideas.py
│   └── chunking.py
├── api.py          # Flask API implementation
└── run.py          # API server entry point
```

## Testing

Run the API tests:
```bash
python test_services.py
```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 