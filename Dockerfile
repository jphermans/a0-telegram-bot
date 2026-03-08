# Minimal Telegram Bot for Agent Zero
FROM python:3.11-alpine

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Create non-root user
RUN adduser -D -h /app telegrambot

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app/telegram_bot/

# Change ownership
RUN chown -R telegrambot:telegrambot /app

# Switch to non-root user
USER telegrambot

# Run the bot
CMD ["python", "-m", "telegram_bot.bot"]
