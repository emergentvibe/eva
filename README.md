# Eva - AI-Powered Text Processing System

Eva is a comprehensive text processing system that combines a REST API service with a Discord bot interface. It provides advanced text analysis capabilities including summarization, idea extraction, and custom text processing.

## Features

- **Text Summarization**: Generate concise summaries with titles from long text
- **Atomic Idea Extraction**: Extract key atomic ideas with importance ratings
- **Custom Extraction**: Create custom extractions with user-defined prompts
- **Discord Bot Interface**: Interact with the services through Discord
- **REST API**: Programmatic access to all text processing features

## Project Structure

```
eva/
├── semantic_engine_api/  # Core API service
│   ├── services/        # Text processing services
│   │   ├── summarization.py
│   │   ├── extraction.py
│   │   ├── atomic_ideas.py
│   │   └── chunking.py
│   ├── api.py          # Flask API implementation
│   └── run.py          # API server entry point
├── discord_interface.py # Discord bot implementation
├── run_bot.py          # Bot server entry point
├── start.py            # Combined API + Bot starter
├── utils.py            # Shared utilities
└── requirements.txt    # Project dependencies
```

## Prerequisites

- Python 3.8+
- Anthropic API key
- Discord Bot Token (for bot functionality)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd eva
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a `.env` file with:
   ```
   ANTHROPIC_API_KEY=your_anthropic_api_key
   DISCORD_TOKEN=your_discord_bot_token
   PORT=5000  # Optional, defaults to 5000
   ```

## Running the System

### Running Just the API

```bash
python semantic_engine_api/run.py
```

### Running Just the Discord Bot

```bash
python run_bot.py
```

### Running Both API and Bot

```bash
python start.py
```

### Production Deployment

For production API deployment:
```bash
gunicorn -w 4 -b 0.0.0.0:5000 'semantic_engine_api.api:create_app()'
```

## API Endpoints

### Health Check
```
GET /api/health
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

## Discord Bot Commands

- `/summarize <text>` - Generate a summary of the provided text
- `/extract <text>` - Extract atomic ideas from the text
- `/custom <text> <prompt>` - Perform custom extraction with a specific prompt

## Development

1. Create a new branch for your feature
2. Make your changes
3. Run tests to ensure everything works
4. Submit a pull request

## Testing

Run the service tests:
```bash
python test_services.py
```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 