# Eva - AI-Powered Discord Bot

Eva is an advanced Discord bot that combines voice interaction, text processing, and AI capabilities to provide a rich interactive experience. It features voice recording, transcription, summarization, and intelligent text processing.

## Features

- **Voice Interaction**
  - Join/leave voice channels
  - Record voice messages with start/stop controls
  - Automatic transcription of voice messages
  - Multi-user voice recording support

- **Text Processing**
  - Message summarization (triggered by 🤖 reaction)
  - Atomic idea extraction
  - Custom text analysis
  - Intelligent prompt answering

- **Voice Commands**
  - `/join` - Join the user's voice channel
  - `/leave` - Leave the current voice channel
  - `/ping` - Check bot latency

## Project Structure

```
eva/
├── semantic_engine_api/  # Core API service (see semantic_engine_api/README.md)
├── run_bot.py          # Bot server entry point
├── start.py            # Combined API + Bot starter
├── utils.py            # Shared utilities
└── requirements.txt    # Project dependencies
```

## Prerequisites

- Python 3.8+
- Anthropic API key
- Discord Bot Token
- Voice channel permissions in Discord

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

## Running the Bot

### Running Just the Bot

```bash
python run_bot.py
```

### Running Both API and Bot

```bash
python start.py
```

## Bot Usage

### Voice Channel Commands

1. `/join` - Makes the bot join your current voice channel
2. `/leave` - Makes the bot leave the voice channel
3. `/ping` - Check the bot's latency

### Voice Recording

1. Join a voice channel and use `/join` to bring the bot in
2. Click the "Start" button to begin recording
3. Speak your message
4. Click the "Stop" button to end recording
5. The bot will transcribe and process your message

### Message Summarization

1. React to any message with the 🤖 emoji
2. The bot will generate a summary with a title
3. The summary will be sent as a reply to the original message

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