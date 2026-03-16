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
| 📁 **Project Support** | Select and switch between A0 projects |
| 📋 **Command Support** | `/start`, `/help`, `/status`, `/projects`, `/project`, `/newchat`, `/reset`, `/cancel` |
| 📱 **Command Menu** | Visual command menu in Telegram UI (type `/` to see) |
| ⌨️ **Animated Typing Indicators** | Shows "typing..." animation while processing |
| 🔐 **User Authentication** | Restrict access by Telegram user ID |
| 🐳 **Docker Ready** | Runs in its own container |
| 📊 **Structured Logging** | JSON logs for production environments |
| 📎 **File Attachments** | Send documents, photos, videos to A0 |
| 🔄 **Auto Context Recovery** | Automatically handles A0 restarts gracefully |

---

## 🆕 Recent Updates

### v1.4.2 (2026-03-16)

- **🔄 Context Error Recovery Fix**: Fixed bug where "Context not found" (404) errors weren't detected properly:
  - Error was being checked in wrong field (`resp.response` instead of `resp.error`)
  - Bot now correctly detects 404 errors and automatically creates a fresh conversation
  - User gets notified: "🔄 Context expired - started fresh chat"
- **📂 Normal Workdir Button**: Added option to deselect project and use default workdir:
  - New "📂 Normal Workdir (no project)" button in `/projects` menu
  - Clears both `current_project` and `context_id` when selected
  - Allows switching back to default workdir from any project
- **📊 `/info` Command**: New command to show session details:
  - Displays: user info, context ID, message count, current project
  - Message count tracks messages in current conversation
  - Resets when context is cleared
- **🔧 `/version` Command**: New command to show bot version info:
  - Shows version number, git commit hash, and last update date
- **🔄 Retry Logic with Exponential Backoff**: Improved error handling:
  - Auto-retry up to 3 times for transient errors
  - Special handling for 503 (busy) and 504 (timeout) errors
  - User-friendly error messages for each HTTP status code
- **⌨️ Menu Enhancements**: Added new buttons to main menu:
  - 📊 Info button for session details
  - 🔧 Version button for bot version
- **📏 Message Length Warning**: Warns if message exceeds 4000 characters:
  - Prevents unexpected truncation
  - Suggests splitting long messages
- **⏳ Rate Limiting**: Protects bot from spam:
  - Max 5 messages per 60 seconds per user
  - Shows wait time when limit exceeded

### v1.4.1 (2026-03-16)

- **🔄 Context Error Recovery Fix**: Fixed bug where "Context not found" (404) errors weren't being detected properly:
  - Error was being checked in wrong field (`resp.response` instead of `resp.error`)
  - Bot now correctly detects 404 errors and automatically creates a fresh conversation
  - User gets notified: "🔄 Context expired - started fresh chat"
- **📂 Normal Workdir Button**: Added option to deselect project and use default workdir:
  - New "📂 Normal Workdir (no project)" button in `/projects` menu
  - Clears both `current_project` and `context_id` when selected
  - Allows switching back to default workdir from any project
- **🐛 Syntax Fix**: Fixed syntax error in handler that was causing bot to crash

### v1.4.0 (2026-03-11)

- **📁 Project Support**: Full integration with A0 projects:
  - `/projects` - List all available A0 projects
  - `/project <name>` - Select a project to work in
  - `/newchat` - Start a fresh conversation (clears context)
  - When a project is selected, the agent works in that project's directory
  - Context is automatically cleared when switching projects
- **🔧 Project API Fix**: Fixed `project_name` parameter to properly communicate with A0 API
- **🔄 Smart Context Handling**: Project is only set on first message of a new conversation

### v1.3.0 (2026-03-09)

- **⌨️ Animated Typing Indicators**: The bot now shows continuous animated "typing..." indicators while processing requests:
  - ✍️ **Typing** - When processing text messages
  - 📷 **Uploading photo** - When uploading photos
  - 📎 **Uploading document** - When uploading documents
  - 🎬 **Uploading video** - When uploading videos
  - 🎤 **Recording voice** - When uploading voice messages
  - Indicators refresh automatically every 4.5 seconds until the response is ready

### v1.2.0 (2026-03-09)

- **📱 Command Menu**: Added visual command menu in Telegram UI - users can now type `/` or click the menu button to see all available commands with descriptions and emojis

### v1.1.0 (2026-03-08)

- **🔄 Automatic Context Recovery**: When A0 restarts and loses conversation context, the bot automatically detects "Context not found" errors and creates a fresh conversation - no more 404 errors!
- **📎 Base64 Attachment Encoding**: Files are now properly encoded as base64 before being sent to A0, ensuring PDFs and other documents are processed correctly.
- **📁 Unified File Structure**: Root level files are now synced with the `telegram_bot/` subfolder to prevent build issues.

---

## 📁 Project Support

The bot now supports A0 projects, allowing you to work within specific project directories:

### Project Commands

| Command | Description |
|---------|-------------|
| `/projects` | List all available A0 projects |
| `/project <name>` | Select a project to work in |
| `/newchat` | Start a fresh conversation (clears context) |

### How Project Selection Works

1. Send `/projects` to see available projects
2. Select a project with `/project myproject`
3. The bot confirms selection and clears any existing context
4. Send your first message - it will be processed in the selected project's directory
5. The agent will have access to project-specific files, instructions, and settings

### Important Notes

- **Project is set on first message only** - The project is activated when you send your first message after selecting it
- **Use /newchat for fresh start** - If you want to continue in the same project but start fresh, use `/newchat`
- **Context persists per project** - Your conversation context is maintained within the selected project

---

## ⌨️ Animated Typing Indicators

The bot shows animated indicators to provide visual feedback while processing requests:

| Action | When Shown | Visual Indicator |
|--------|-----------|------------------|
| `typing` | Text messages, processing | ✍️ "typing..." |
| `upload_photo` | Uploading photos | 📷 "uploading photo..." |
| `upload_document` | Uploading documents | 📎 "uploading document..." |
| `upload_video` | Uploading videos | 🎬 "uploading video..." |
| `record_voice` | Uploading voice | 🎤 "recording voice..." |

### How It Works

1. User sends a message or file
2. Bot immediately shows the appropriate animated indicator
3. Indicator refreshes every 4.5 seconds (Telegram expires after 5s)
4. Indicator automatically stops when response arrives
5. Response is sent to the user

This provides a smooth, professional user experience with continuous visual feedback.

---

## 🤝 Community Maintenance & Pull Requests

This project is **community-maintained**! Users are encouraged to contribute improvements, bug fixes, and new features through **Pull Requests**.

### How to Contribute

1. **Fork** the repository
2. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/my-improvement
   ```
3. **Make your changes** and test them
4. **Commit** with a clear message:
   ```bash
   git commit -am "fix: Description of the fix"
   ```
5. **Push** to your fork:
   ```bash
   git push origin feature/my-improvement
   ```
6. **Open a Pull Request** on GitHub

### Types of Contributions Welcome

- 🐛 **Bug fixes** - Found an issue? Fix it and submit a PR!
- ✨ **New features** - Add new commands, integrations, or capabilities
- 📝 **Documentation** - Improve README, add examples, clarify instructions
- 🌍 **Translations** - Help make the bot accessible to more users
- 🧪 **Tests** - Add unit tests or integration tests

### Pull Request Guidelines

- Base your PR on the `main` branch
- Keep changes focused and atomic
- Test your changes before submitting
- Update documentation if needed

Your contributions help make this bot better for everyone! 🙌

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
mkdir -p ~/a0-telegram-bot
cd ~/a0-telegram-bot
```

### 3. Clone the Repository

```bash
git clone https://github.com/jphermans/a0-telegram-bot.git .
```

### 4. Create Environment File

```bash
nano .env
```

Paste your configuration:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ALLOWED_USERS=your_user_id_here
A0_ENDPOINT=http://agent-zero:80
A0_API_KEY=your_a0_api_key_here
```

### 5. Build and Start

```bash
# Build the container
docker compose build --no-cache

# Start the bot
docker compose up -d

# Check logs
docker compose logs -f
```

---

## 🖥️ Option B: Docker Desktop (Windows/Mac/Linux Desktop)

For local development with Docker Desktop.

### 1. Clone Repository

```bash
git clone https://github.com/jphermans/a0-telegram-bot.git
cd a0-telegram-bot
```

### 2. Create .env File

Create `.env` file in the project root:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ALLOWED_USERS=your_user_id_here
A0_ENDPOINT=http://host.docker.internal:8000
A0_API_KEY=your_a0_api_key_here
```

> 💡 **Note:** `host.docker.internal` allows the container to access services on your host machine.

### 3. Build and Run

```bash
docker compose build
docker compose up -d
```

---

## 🌐 Option C: Existing A0 Docker Compose

Add the Telegram bot to your existing A0 docker-compose.yml.

### 1. Copy Files

Copy the `a0-telegram-bot` folder to your A0 directory:

```bash
cp -r a0-telegram-bot /path/to/your/a0/
```

### 2. Update docker-compose.yml

Add this service to your existing `docker-compose.yml`:

```yaml
services:
  # ... your existing services ...

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
      - SHARED_VOLUME_PATH=/shared
    volumes:
      - a0-shared:/shared

volumes:
  a0-shared:
    driver: local
```

### 3. Add to .env

Add your Telegram credentials to your existing `.env` file:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ALLOWED_USERS=your_user_id_here
```

### 4. Deploy

```bash
docker compose build telegram-bot --no-cache
docker compose up -d telegram-bot
```

---

## 💬 Usage

### Commands

| Command | Description |
|---------|-------------|
| `/start` | Initialize bot and show welcome message |
| `/help` | Display help information |
| `/status` | Check A0 connection status and current project |
| `/projects` | List all available A0 projects |
| `/project <name>` | Select a project to work in |
| `/newchat` | Start a fresh conversation |
| `/reset` | Reset conversation context |
| `/cancel` | Cancel any pending operation |

### Sending Messages

Simply send any text message to the bot, and it will forward it to A0 for processing.

### Sending Files

Send any file (document, photo, video, voice message) with an optional caption:

- **Documents**: PDF, DOCX, TXT, etc.
- **Photos**: JPG, PNG, etc.
- **Videos**: MP4, MOV, etc.
- **Voice**: OGG (Telegram default)

---

## 📎 File Attachments

Files are **base64-encoded** and sent directly to A0 for reliable processing.

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
2. Type `/` to see the command menu
3. Send `/start`
4. Send `/status` to check A0 connection
5. Send `/projects` to see available projects
6. Select a project with `/project <name>`
7. Send a text message to test AI response
8. Send a PDF to test file attachments

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

### Project Not Activating

1. Make sure you've rebuilt the container with the latest code:
   ```bash
   git pull origin main
   docker compose build telegram-bot --no-cache
   docker compose up -d telegram-bot
   ```
2. Use `/newchat` after selecting a project to start fresh
3. The project is only set on the **first message** of a new conversation

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

### Command Menu Not Showing

1. The command menu is set automatically when the bot starts
2. Try restarting the bot: `docker compose restart telegram-bot`
3. Type `/` in the chat to trigger the menu

### Typing Indicator Not Showing

1. The indicator should appear automatically when sending messages
2. Check logs for any errors related to chat actions
3. Try restarting the bot: `docker compose restart telegram-bot`

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
├── bot.py                   # Main bot application (with command menu)
├── handlers.py              # Command and message handlers
├── typing_indicator.py      # Continuous animated typing indicators
├── project_discovery.py     # A0 project discovery and management
├── a0_client.py             # A0 API client (base64 encoding)
├── auth.py                  # User authentication
├── config.py                # Configuration management
└── logging_config.py        # Structured logging
```

---

## 📝 License

This project is licensed under the MIT License.

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/jphermans/a0-telegram-bot/issues)
- **Pull Requests**: Contributions welcome! See [Community Maintenance](#-community-maintenance--pull-requests) section
- **Agent Zero**: [https://github.com/agent0ai/agent-zero](https://github.com/agent0ai/agent-zero)

---

Made with ❤️ for the Agent Zero community using [Agent Zero](https://github.com/agent0ai/agent-zero)
