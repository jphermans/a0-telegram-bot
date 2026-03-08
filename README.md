# A0 Telegram Bot

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](Dockerfile)
[![Made with Agent Zero](https://img.shields.io/badge/made%20with-Agent%20Zero-purple.svg)](https://github.com/agent0ai/agent-zero)

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
| 📎 **File Attachments** | Send documents, photos, videos to A0 |
| 🔄 **Auto Context Recovery** | Automatically handles A0 restarts gracefully |

---

## 🆕 Recent Updates

### v1.1.0 (2026-03-08)

- **🔄 Automatic Context Recovery**: When A0 restarts and loses conversation context, the bot automatically detects "Context not found" errors and creates a fresh conversation - no more 404 errors!
- **📎 Base64 Attachment Encoding**: Files are now properly encoded as base64 before being sent to A0, ensuring PDFs and other documents are processed correctly.
- **📁 Unified File Structure**: Root level files are now synced with the `telegram_bot/` subfolder to prevent build issues.

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
3. Click on **Settings** (gear icon ⚙️)
4. Go to **External Services** → **External API**
5. Click **"Show examples"** button
6. Find your API key in the examples shown

> ⚠️ **Note:** The A0 API Key is different from your LLM provider API key!

### Step 4: Clone and Configure

```bash
# Clone the repository (main branch is default)
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

Choose the setup that matches your environment:

---

## 🖥️ Option A: Headless Server (Linux VPS)

For servers accessed via SSH (e.g., DigitalOcean, AWS, Hetzner, home server).

### 1. SSH into Your Server

```bash
ssh user@your-server-ip
```

### 2. Create Project Directory

```bash
mkdir -p ~/a0-telegram
cd ~/a0-telegram
```

### 3. Clone Repository

```bash
git clone https://github.com/jphermans/a0-telegram-bot.git
```

### 4. Create .env File

```bash
cp a0-telegram-bot/env.example .env
nano .env
```

Edit with your credentials:

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-123456
TELEGRAM_ALLOWED_USERS=123456789
A0_ENDPOINT=http://agent-zero:80
A0_API_KEY=your_a0_api_key_here
```

### 5. Create docker-compose.yml

```bash
nano docker-compose.yml
```

```yaml
services:
  agent-zero:
    image: agent0ai/agent-zero:latest
    container_name: agent-zero
    restart: unless-stopped
    ports:
      - "5030:80"
    volumes:
      - ./a0-data:/a0/usr
      - a0-shared:/a0/usr/workdir/shared  # Shared volume for attachments
    environment:
      - AUTH_LOGIN=admin
      - AUTH_PASSWORD=your_password_here

  telegram-bot:
    build:
      context: ./a0-telegram-bot
      dockerfile: Dockerfile
    container_name: a0-telegram-bot
    restart: unless-stopped
    depends_on:
      - agent-zero
    volumes:
      - a0-shared:/shared  # Shared volume for attachments
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_ALLOWED_USERS=${TELEGRAM_ALLOWED_USERS}
      - A0_ENDPOINT=http://agent-zero:80
      - A0_API_KEY=${A0_API_KEY}
      - SHARED_VOLUME_PATH=/shared

volumes:
  a0-shared:
    driver: local
```

### 6. Deploy

```bash
# Pull latest code
cd a0-telegram-bot && git pull origin main && cd ..

# Build and start (use --no-cache to ensure fresh build)
docker compose build telegram-bot --no-cache
docker compose up -d telegram-bot

# Check logs
docker logs -f a0-telegram-bot
```

### 7. Verify

```bash
# Check containers are running
docker ps

# Should show both containers:
# - agent-zero
# - a0-telegram-bot
```

---

## 💻 Option B: Docker Desktop (Windows/macOS)

For local development using Docker Desktop GUI.

### 1. Prepare Project Folder

Create a folder on your computer:

- **Windows:** `C:\Users\YourName\a0-telegram`
- **macOS:** `~/a0-telegram`

### 2. Clone Repository

Open Terminal (macOS) or PowerShell (Windows):

```bash
# Navigate to folder
cd ~/a0-telegram  # macOS
# or
cd C:\Users\YourName\a0-telegram  # Windows

# Clone repository
git clone https://github.com/jphermans/a0-telegram-bot.git
```

### 3. Create .env File

Create `.env` file in the project root (same level as docker-compose.yml):

```bash
cp a0-telegram-bot/env.example .env
```

Edit with your credentials:

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-123456
TELEGRAM_ALLOWED_USERS=123456789
A0_ENDPOINT=http://agent-zero:80
A0_API_KEY=your_a0_api_key_here
```

### 4. Create docker-compose.yml

Create `docker-compose.yml` in the project root:

```yaml
services:
  agent-zero:
    image: agent0ai/agent-zero:latest
    container_name: agent-zero
    restart: unless-stopped
    ports:
      - "5030:80"
    volumes:
      - ./a0-data:/a0/usr

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

### 5. Build and Run in Docker Desktop

**Using Docker Desktop GUI:**

1. Open **Docker Desktop**
2. Go to **Containers** tab
3. Click **"Import** or use terminal

**Using Terminal/PowerShell:**

```bash
# Navigate to project folder
cd ~/a0-telegram  # macOS
# or
cd C:\Users\YourName\a0-telegram  # Windows

# Pull latest code
cd a0-telegram-bot && git pull origin main && cd ..

# Build and start
docker compose build telegram-bot --no-cache
docker compose up -d telegram-bot

# Check logs
docker compose logs -f telegram-bot
```

### 6. Access A0 Web UI

Open browser: `http://localhost:5030`

### 7. Folder Structure (Docker Desktop)

```
a0-telegram/
├── docker-compose.yml      # Main compose file
├── .env                    # Your credentials
├── a0-data/                # A0 persistent data
└── a0-telegram-bot/        # Bot source code
    ├── Dockerfile
    ├── requirements.txt
    ├── bot.py
    ├── handlers.py
    ├── a0_client.py
    ├── auth.py
    ├── config.py
    └── logging_config.py
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

## 📎 File Attachments

The bot supports sending file attachments to A0 for processing. Files are **base64-encoded** and sent directly to A0 for reliable processing.

### Supported File Types

| Type | Extensions | Max Size |
|------|------------|----------|
| 📷 **Photos** | .jpg, .png, .gif, .webp | 20 MB |
| 📄 **Documents** | .pdf, .txt, .docx, .xlsx, .csv, etc. | 20 MB |
| 🎤 **Voice Messages** | .ogg (Telegram default) | 20 MB |
| 🎬 **Videos** | .mp4, .mov, .avi | 20 MB |

### Usage Examples

**Send a document for analysis:**
```
User: [sends PDF file with caption "Summarize this document"]
Bot: [A0 analyzes the PDF and provides a summary]
```

**Send a photo with a caption:**
```
User: [sends photo with caption "What do you see in this image?"]
Bot: [A0 describes or analyzes the image]
```

### How It Works

1. You send an attachment to the bot
2. The bot downloads the file securely
3. File is **base64-encoded** and sent to A0 API
4. A0 processes the attachment
5. Response is sent back to you
6. Temporary files are automatically cleaned up

---

## 🔄 Automatic Context Recovery

The bot automatically handles A0 restarts gracefully:

- **Problem**: When A0 restarts, it loses all conversation contexts stored in memory
- **Solution**: The bot detects "Context not found" errors and automatically creates a fresh conversation

**What happens when A0 restarts:**
```
User: [sends message]
Bot: 🔄 Previous conversation context was lost (A0 may have restarted). Starting a fresh conversation.
Bot: [processes message in new context]
```

No manual intervention required! The bot continues working seamlessly.

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
5. Send a PDF to test file attachments

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

### API Key Required Error (401)

1. Make sure `A0_API_KEY` is set in your `.env` file
2. Make sure `A0_API_KEY` is passed in docker-compose environment variables
3. Verify the API key is correct from A0 Web UI:
   - Settings → External Services → External API → Show examples

### Context Not Found Error (404)

This is now handled automatically! The bot will:
1. Detect the error
2. Create a fresh conversation
3. Notify you and continue processing

If you still see issues, try `/reset` to manually reset the conversation.

### PDF/Document Not Being Processed

1. Make sure you've rebuilt the container with the latest code:
   ```bash
   git pull origin main
   docker compose build telegram-bot --no-cache
   docker compose up -d telegram-bot
   ```
2. Check logs for any encoding errors
3. Ensure the file size is under 20MB

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
├── a0_client.py             # A0 API client (base64 encoding)
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
2. Create a feature branch from `main`: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -am 'Add my feature'`
4. Push to branch: `git push origin feature/my-feature`
5. Submit a Pull Request

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/jphermans/a0-telegram-bot/issues)
- **Agent Zero**: [https://github.com/agent0ai/agent-zero](https://github.com/agent0ai/agent-zero)

---

Made with ❤️ for the Agent Zero community using [Agent Zero](https://github.com/agent0ai/agent-zero)
