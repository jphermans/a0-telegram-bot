# A0 Telegram Bot

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](Dockerfile)

A production-ready Telegram bot integration for **Agent Zero (A0)** - enabling full bidirectional communication between Telegram and the A0 AI agent framework.

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔄 **Bidirectional Communication** | Send and receive messages between Telegram and A0 |
| 🤖 **Natural Language** | Conversational AI interaction through Telegram |
| 📋 **Command Support** | `/start`, `/help`, `/status`, `/tasks`, `/cancel`, `/reset` |
| 📎 **Attachments** | Photos, documents, videos, voice messages |
| 🔐 **User Authentication** | Restrict access by Telegram user ID |
| 📦 **Message Chunking** | Auto-split long messages (4096 char limit) |
| 🔄 **Auto-Reconnect** | Resilient connection handling |
| 🐳 **Docker Ready** | Runs in its own container |
| 📊 **Structured Logging** | JSON logs for production environments |

## 🏗️ Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│    Telegram     │◄────►│  Telegram Bot   │◄────►│   Agent Zero    │
│     Users       │      │   Container     │      │   (A0 API)      │
└─────────────────┘      └─────────────────┘      └─────────────────┘
                           
                           ├── bot.py         (Main entry point)
                           ├── handlers.py    (Command handlers)
                           ├── a0_client.py   (A0 API client)
                           ├── auth.py        (User authentication)
                           └── config.py      (Configuration)
```

## 📁 Project Structure

```
a0-telegram-bot/
├── __init__.py              # Package initialization
├── bot.py                   # Main bot application (entry point)
├── handlers.py              # Command and message handlers
├── a0_client.py             # A0 API client for HTTP communication
├── auth.py                  # User authentication by Telegram ID
├── config.py                # Configuration management
├── logging_config.py        # Structured logging setup
├── Dockerfile               # Docker image definition
├── requirements.txt         # Python dependencies
├── docker-compose.snippet.yml  # Docker Compose service
├── .env.example             # Example environment configuration
├── .gitignore               # Git ignore rules
└── README.md                # This file
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Agent Zero running in Docker
- A Telegram bot token (from [@BotFather](https://t.me/botfather))
- Your Telegram user ID (from [@userinfobot](https://t.me/userinfobot))

### 1. Create Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the instructions
3. Save the bot token (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Get Your User ID

1. Open Telegram and search for **@userinfobot**
2. Start a conversation - it will reply with your numeric user ID
3. Save this ID for the allowed users list

### 3. Configure Environment

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/a0-telegram-bot.git
cd a0-telegram-bot

# Create environment file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### 4. Add to Docker Compose

Add this service to your Agent Zero `docker-compose.yml`:

```yaml
services:
  telegram-bot:
    build: ./a0-telegram-bot
    container_name: a0-telegram-bot
    restart: unless-stopped
    depends_on:
      - agent-zero
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_ALLOWED_USERS=${TELEGRAM_ALLOWED_USERS}
      - A0_ENDPOINT=http://agent-zero:8000
    networks:
      - default
```

### 5. Build and Run

```bash
# Build and start the bot
docker compose up -d telegram-bot

# Check logs
docker logs -f a0-telegram-bot
```

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|--------|
| `TELEGRAM_BOT_TOKEN` | ✅ | Bot token from @BotFather | `123456:ABC-DEF...` |
| `TELEGRAM_ALLOWED_USERS` | ✅ | Comma-separated user IDs | `123456789,987654321` |
| `A0_ENDPOINT` | ✅ | A0 API URL | `http://agent-zero:8000` |
| `LOG_LEVEL` | ❌ | Logging level | `INFO` (default) |
| `A0_TIMEOUT` | ❌ | API timeout in seconds | `300` (default) |
| `A0_API_KEY` | ❌ | API key if A0 requires auth | `your-api-key` |

### Example .env File

```env
# Telegram Configuration
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_ALLOWED_USERS=123456789,987654321

# A0 Configuration
A0_ENDPOINT=http://agent-zero:8000
A0_TIMEOUT=300

# Optional
LOG_LEVEL=INFO
```

## 📋 Commands Reference

| Command | Description | Example |
|---------|-------------|--------|
| `/start` | Initialize bot and show welcome message | `/start` |
| `/help` | Display help and usage instructions | `/help` |
| `/status` | Check A0 connection status | `/status` |
| `/tasks` | List scheduled tasks in A0 | `/tasks` |
| `/cancel` | Cancel current operation | `/cancel` |
| `/reset` | Reset conversation context | `/reset` |

### Natural Language

Send any text message to interact with A0 naturally:

```
User: What's the weather like today?
A0: I'll check the weather for you...
```

### Attachments

Send photos, documents, videos, or voice messages:

```
User: [Sends photo]
A0: I received your image. What would you like me to do with it?
```

## 🔐 Security

### User Authorization

- Only users listed in `TELEGRAM_ALLOWED_USERS` can interact with the bot
- Unauthorized users receive an access denied message
- All access attempts are logged

### Best Practices

1. **Never commit `.env` files** - Use `.env.example` for templates
2. **Rotate bot tokens** if compromised
3. **Limit user access** to trusted individuals only
4. **Monitor logs** for suspicious activity

## 🧪 Testing

### Check Bot Status

```bash
# View container status
docker ps | grep a0-telegram

# View logs
docker logs -f a0-telegram-bot

# Test from Telegram
# 1. Start chat with your bot
# 2. Send /start
# 3. Send /status
# 4. Send a text message
```

### Debug Mode

```bash
# Run with debug logging
docker compose run --rm -e LOG_LEVEL=DEBUG telegram-bot
```

## 🐛 Troubleshooting

### Bot Not Responding

1. Check if the bot is running: `docker ps | grep a0-telegram`
2. Check logs: `docker logs a0-telegram-bot`
3. Verify bot token is correct
4. Ensure your user ID is in allowed users

### Connection to A0 Failed

1. Verify A0 is running: `docker ps | grep agent-zero`
2. Check A0 endpoint is correct
3. Ensure both containers are on the same network

### Permission Denied

1. Get your user ID from @userinfobot
2. Add it to `TELEGRAM_ALLOWED_USERS`
3. Restart the bot: `docker compose restart telegram-bot`

## 📊 Logging

The bot uses structured JSON logging:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "logger": "a0_telegram_bot",
  "message": "Message received",
  "user_id": 123456789,
  "command": "status"
}
```

## 🔄 Updates

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker compose up -d --build telegram-bot
```

## 📝 License

This project is licensed under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -am 'Add my feature'`
4. Push to branch: `git push origin feature/my-feature`
5. Submit a Pull Request

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/jphermans/a0-telegram-bot/issues)
- **Documentation**: See `docs/` folder for detailed guides

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot library
- [Agent Zero](https://github.com/your-org/agent-zero) - AI agent framework

---

Made with ❤️ for the Agent Zero community
