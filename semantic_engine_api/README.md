# Eva API Module

A REST API service that provides text processing functionality including summarization and idea extraction.

## Features

- **Text Summarization**: Generate concise summaries with titles from long text
- **Atomic Idea Extraction**: Extract key atomic ideas with importance ratings from text
- **Custom Extraction**: Create custom extractions with your own prompts

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd api_module
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   Create a `.env` file with the following:
   ```
   ANTHROPIC_API_KEY=your_anthropic_api_key
   PORT=5000  # Optional, defaults to 5000
   ```

## Running the API

Start the API server:

```
python run.py
```

Or for production:

```
gunicorn -w 4 -b 0.0.0.0:5000 'api:create_app()'
```

## API Endpoints

### Health Check

```
GET /api/health
```

Returns the status of the API.

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
  "title": "Concise Title",
  "summary": "Detailed summary of the text..."
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
      "text": "First key idea",
      "score": 5
    },
    {
      "text": "Second key idea",
      "score": 3
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
  "result": [
    {
      "text": "Extracted item 1",
      "score": 4
    },
    {
      "text": "Extracted item 2",
      "score": 2
    }
  ]
}
```

## Development

To contribute to the API module, please follow these steps:

1. Create a new branch for your feature
2. Make your changes
3. Run tests to ensure everything works
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 