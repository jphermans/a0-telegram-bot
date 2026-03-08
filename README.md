# A0 Telegram Bot

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](Dockerfile)

A production-ready Telegram bot integration for **Agent Zero (A0)** - enabling full bidirectional communication between Telegram and the A0 AI agent framework.

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔄 **Bidirectional Communication** | Send and receive messages between Telegram and A0 |
| 🤖 **Natural Language** | Conversational AI interaction through Telegram |
| 📋 **Command Support** | `/start`, `/help`, `/status`, `/reset` |
| 🔐 **User Authentication** | Restrict access by Telegram user ID |
| 🐳 **Docker Ready** | Runs in its own container |
| 📊 **Structured Logging** | JSON logs for production environments |

---

## 📋 Prerequisites

Before you begin, ensure you have:

1. **Docker** or **Docker Desktop** installed
2. **Agent Zero** running and accessible
3. **Telegram Bot Token** from @BotFather
4. **Your Telegram User ID** from @userinfobot
5. **A0 API Key** from A0 Web UI Settings

---

## 🚀 Quick Start

### Step 1: Get Telegram Bot Token

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the instructions
3. Copy the bot token (format: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-123456`)

### Step 2: Get Your Telegram User ID

1. Open Telegram and search for **@userinfobot**
2. It will reply with your numeric user ID (e.g., `123456789`)

### Step 3: Get A0 API Key

1. Open your **A0 Web UI** in browser (e.g., `http://localhost:5030`)
2. Login with your credentials
3. Go to **Settings** (gear icon ⚙️)
4. Find **"API Keys"** section
5. Copy the API key

> ⚠️ **Note:** The A0 API Key is different from your LLM provider API key!

### Step 4: Clone and Configure

```bash
# Clone the repository
git clone https://github.com/jphermans/a0-telegram-bot.git
cd a0-telegram-bot

# Create environment file from example
cp env.example .env

# Edit .env with your credentials
nano .env
```

### Step 5: Configure .env File

```env
# Telegram Configuration
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-123456
TELEGRAM_ALLOWED_USERS=123456789

# A0 Configuration
A0_ENDPOINT=http://agent-zero:80
A0_API_KEY=your_a0_api_key_here
A0_TIMEOUT=300

# Optional
LOG_LEVEL=INFO
```

---

## 🐳 Docker Setup

### Option A: Docker Compose (Recommended)

Add the telegram bot service to your existing A0 `docker-compose.yml`:

```yaml
services:
  # Your existing A0 service
  agent-zero:
    image: agent0ai/agent-zero:latest
    ports:
      - "5030:80"
    # ... your existing config ...

  # Add Telegram bot service
  telegram-bot:
    build:
      context: ./a0-telegram-bot
      dockerfile: Dockerfile
    container_name: a0-telegram-bot
    restart: unless-stopped
    depends_on:
      - agent-zero
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_ALLOWED_USERS=${TELEGRAM_ALLOWED_USERS}
      - A0_ENDPOINT=http://agent-zero:80
      - A0_API_KEY=${A0_API_KEY}
```

### Option B: Docker Desktop (Windows/macOS)

If you're using Docker Desktop on Windows or macOS:

#### 1. Prepare Project Folder

Create a folder structure like this:

```
project-folder/
├── docker-compose.yml
├── .env
└── a0-telegram-bot/
    ├── Dockerfile
    ├── requirements.txt
    ├── __init__.py
    ├── bot.py
    ├── handlers.py
    ├── a0_client.py
    ├── auth.py
    ├── config.py
    └── logging_config.py
```

#### 2. Create docker-compose.yml

```yaml
services:
  agent-zero:
    image: agent0ai/agent-zero:latest
    ports:
      - "5030:80"
    container_name: agent-zero
    restart: unless-stopped

  telegram-bot:
    build:
      context: ./a0-telegram-bot
      dockerfile: Dockerfile
    container_name: a0-telegram-bot
    restart: unless-stopped
    depends_on:
      - agent-zero
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_ALLOWED_USERS=${TELEGRAM_ALLOWED_USERS}
      - A0_ENDPOINT=http://agent-zero:80
      - A0_API_KEY=${A0_API_KEY}
```

#### 3. Create .env File

Create a `.env` file in the same folder as `docker-compose.yml`:

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-123456
TELEGRAM_ALLOWED_USERS=123456789
A0_API_KEY=your_a0_api_key_here
```

#### 4. Open Terminal in Docker Desktop

1. Open **Docker Desktop**
2. Go to **Containers** tab
3. Click **"Open in terminal"** or use your system terminal
4. Navigate to your project folder:

```bash
# Windows (PowerShell)
cd C:\Users\YourName\project-folder

# macOS
~/project-folder
```

#### 5. Build and Run

```bash
# Build the containers
docker compose build

# Start the containers
docker compose up -d

# Check logs
docker compose logs -f telegram-bot
```

---

## ⚙️ Configuration Reference

### Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|--------|
| `TELEGRAM_BOT_TOKEN` | ✅ | Bot token from @BotFather | `1234567890:ABCdef...` |
| `TELEGRAM_ALLOWED_USERS` | ✅ | Comma-separated user IDs | `123456789,987654321` |
| `A0_ENDPOINT` | ✅ | A0 API URL | `http://agent-zero:80` |
| `A0_API_KEY` | ✅ | API key from A0 Settings | `abc123-def456...` |
| `A0_TIMEOUT` | ❌ | Request timeout in seconds | `300` (default) |
| `LOG_LEVEL` | ❌ | Logging level | `INFO` (default) |

### A0_ENDPOINT Options

| Scenario | Value |
|----------|-------|
| Docker (same network) | `http://agent-zero:80` |
| Local development | `http://localhost:5030` |
| Remote server | `http://your-server-ip:5030` |

> **Important:** Inside Docker, use the **service name** from your docker-compose.yml, NOT `localhost`!

---

## 📋 Commands Reference

| Command | Description |
|---------|-------------|
| `/start` | Initialize bot and show welcome message |
| `/help` | Display help and usage instructions |
| `/status` | Check A0 connection status |
| `/reset` | Reset conversation context |

---

## 🔐 Security

### User Authorization

- Only users listed in `TELEGRAM_ALLOWED_USERS` can interact with the bot
- Unauthorized users receive an access denied message
- All access attempts are logged

### Best Practices

1. **Never commit `.env` files** - Use `env.example` for templates
2. **Rotate bot tokens** if compromised
3. **Limit user access** to trusted individuals only
4. **Monitor logs** for suspicious activity

---

## 🧪 Testing

### Check Bot Status

```bash
# View container status
docker ps | grep a0-telegram

# View logs
docker logs -f a0-telegram-bot
```

### Test from Telegram

1. Start a chat with your bot
2. Send `/start`
3. Send `/status` to check A0 connection
4. Send a text message to test AI response

### Debug Mode

```bash
# Run with debug logging
docker compose run --rm -e LOG_LEVEL=DEBUG telegram-bot
```

---

## 🐛 Troubleshooting

### Bot Not Responding

1. Check if the bot is running: `docker ps | grep a0-telegram`
2. Check logs: `docker logs a0-telegram-bot`
3. Verify bot token is correct
4. Ensure your user ID is in allowed users

### Connection to A0 Failed

1. Verify A0 is running: `docker ps | grep agent-zero`
2. Check A0 endpoint is correct (use service name, not localhost)
3. Ensure both containers are on the same Docker network

### API Key Required Error

1. Make sure `A0_API_KEY` is set in your `.env` file
2. Make sure `A0_API_KEY` is passed in docker-compose environment variables
3. Verify the API key is correct from A0 Web UI Settings

### Permission Denied

1. Get your user ID from @userinfobot
2. Add it to `TELEGRAM_ALLOWED_USERS` in `.env`
3. Restart the bot: `docker compose restart telegram-bot`

---

## 📁 Project Structure

```
a0-telegram-bot/
├── Dockerfile               # Docker image definition
├── requirements.txt         # Python dependencies
├── docker-compose.snippet.yml  # Docker Compose example
├── env.example              # Environment configuration template
├── .dockerignore            # Docker build exclusions
├── .gitignore               # Git exclusions
├── README.md                # This file
├── __init__.py              # Package initialization
├── bot.py                   # Main bot application
├── handlers.py              # Command and message handlers
├── a0_client.py             # A0 API client
├── auth.py                  # User authentication
├── config.py                # Configuration management
└── logging_config.py        # Structured logging
```

---

## 📝 License

This project is licensed under the MIT License.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -am 'Add my feature'`
4. Push to branch: `git push origin feature/my-feature`
5. Submit a Pull Request

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/jphermans/a0-telegram-bot/issues)
- **Agent Zero**: [https://github.com/agent0ai/agent-zero](https://github.com/agent0ai/agent-zero)

---

Made with ❤️ for the Agent Zero community
