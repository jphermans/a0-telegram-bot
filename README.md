# Telegram Bot for Agent Zero

A Python-based Telegram interface that enables full bidirectional communication with Agent Zero (A0) framework.

## Features

- **Bidirectional Communication**: Send and receive messages between Telegram and A0
- **Command Support**: Built-in commands (/start, /help, /status, /tasks, /cancel, /reset)
- **Natural Language**: Send any text message to interact with A0
- **Attachment Support**: Handle photos, documents, videos, and voice messages
- **User Authentication**: Restrict access to authorized Telegram user IDs
- **Message Chunking**: Automatic splitting of long messages to respect Telegram limits
- **Graceful Error Handling**: Automatic reconnection on network errors
- **Docker Ready**: Runs in its own container with Docker Compose support

## Quick Start

### Prerequisites

1. **Telegram Bot Token**: Get from [@BotFather](https://t.me/botfather) on Telegram
2. **Your Telegram User ID**: Get from [@userinfobot](https://t.me/userinfobot)
3. **Agent Zero**: Running instance accessible via HTTP API

### Configuration

1. Copy the example environment file:
   ```bash
   cp env.example .env
   ```

2. Edit `.env` with your configuration:
   ```env
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_ALLOWED_USERS=123456789,987654321
   A0_ENDPOINT=http://agent-zero:8000
   ```

### Running with Docker Compose

Add this service to your existing `docker-compose.yml`:

```yaml
services:
  telegram-bot:
    build:
      context: ./telegram_bot
      dockerfile: Dockerfile
    container_name: a0-telegram-bot
    restart: unless-stopped
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_ALLOWED_USERS=${TELEGRAM_ALLOWED_USERS}
      - A0_ENDPOINT=http://agent-zero:8000
    networks:
      - default
```

Then run:
```bash
docker compose up -d telegram-bot
```

### Running Locally (Development)

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_ALLOWED_USERS="123456789"
export A0_ENDPOINT="http://localhost:8000"

# Run the bot
python -m telegram_bot.bot
```

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Initialize bot and show welcome message |
| `/help` | Display help and usage instructions |
| `/status` | Check A0 connection status |
| `/tasks` | List scheduled tasks |
| `/cancel` | Cancel current operation |
| `/reset` | Reset conversation context |

## Architecture

```
telegram_bot/
├── __init__.py         # Package initialization and exports
├── bot.py              # Main bot application and entry point
├── handlers.py         # Command and message handlers
├── a0_client.py        # A0 API client for HTTP communication
├── auth.py             # User authentication and authorization
├── config.py           # Configuration management
├── logging_config.py   # Structured logging setup
├── Dockerfile          # Docker image definition
├── requirements.txt    # Python dependencies
├── docker-compose.snippet.yml  # Docker Compose service definition
└── env.example        # Example environment configuration
```

## API Integration

The bot communicates with A0 via the HTTP API:

- **Endpoint**: `POST /api/message`
- **Content-Type**: `multipart/form-data`
- **Request Fields**:
  - `text`: Message text
  - `context`: Conversation context ID (optional)
  - `message_id`: Message identifier (optional)
  - `attachments`: File attachments (optional)

- **Response**:
  ```json
  {
    "message": "Response from A0",
    "context": "context-id"
  }
  ```

## Security

### User Authorization

Only users whose Telegram IDs are in `TELEGRAM_ALLOWED_USERS` can interact with the bot. Unauthorized users receive:
```
⛔ Unauthorized. You are not allowed to use this bot.
```

### Best Practices

1. **Never commit `.env`** files with real credentials
2. Use environment variables or secrets management in production
3. Limit the number of allowed users to essential personnel
4. Monitor logs for unauthorized access attempts
5. Use HTTPS for A0 endpoint in production

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | - | Bot token from @BotFather |
| `TELEGRAM_ALLOWED_USERS` | Yes | - | Comma-separated allowed user IDs |
| `A0_ENDPOINT` | No | `http://localhost:8000` | A0 API endpoint |
| `A0_API_KEY` | No | - | A0 API key (if auth enabled) |
| `A0_TIMEOUT` | No | `120` | Request timeout in seconds |
| `TELEGRAM_POLL_TIMEOUT` | No | `30` | Long polling timeout |
| `TELEGRAM_POLL_INTERVAL` | No | `1.0` | Polling interval in seconds |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `JSON_LOGS` | No | `false` | Use JSON structured logging |
| `ENABLE_ATTACHMENTS` | No | `true` | Enable file attachments |
| `MAX_ATTACHMENT_SIZE` | No | `20971520` | Max attachment size (bytes) |
| `MAX_RETRIES` | No | `5` | Max retry attempts |
| `RETRY_DELAY` | No | `5.0` | Retry delay in seconds |

## Troubleshooting

### Bot not responding

1. Check if bot token is correct
2. Verify user ID is in allowed list
3. Check A0 endpoint is accessible
4. Review logs: `docker logs a0-telegram-bot`

### Multiple bot instances conflict

If you see "Conflict: terminated by other getUpdates request":
1. Stop all bot instances
2. Wait 30 seconds
3. Start single instance

### Connection issues

1. Verify A0 endpoint URL
2. Check network connectivity between containers
3. Ensure A0 is running and healthy

## Testing

### Manual Testing

1. Start a conversation with your bot on Telegram
2. Send `/start` to verify welcome message
3. Send `/status` to check A0 connectivity
4. Send a text message to test A0 integration
5. Send a photo/document to test attachments

### Verifying Deployment

```bash
# Check container status
docker ps | grep a0-telegram

# View logs
docker logs -f a0-telegram-bot

# Check health
docker inspect a0-telegram-bot | grep -A 5 Health
```

## License

MIT License - See LICENSE file for details.
