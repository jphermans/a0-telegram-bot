# Telegram Bot for Agent Zero
# Docker image for running the Telegram interface

FROM python:3.11-slim-bookworm

# Labels for container metadata
LABEL maintainer="Agent Zero Team"
LABEL description="Telegram bot interface for Agent Zero"
LABEL version="1.0.0"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash telegrambot

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the telegram_bot module
COPY . /app/telegram_bot/

# Change ownership to non-root user
RUN chown -R telegrambot:telegrambot /app

# Switch to non-root user
USER telegrambot

# Set Python path to include the app directory
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default environment variables (can be overridden)
ENV LOG_LEVEL=INFO \
    JSON_LOGS=false

# Expose health check port (optional)
EXPOSE 8080

# Run the bot
CMD ["python", "-m", "telegram_bot.bot"]
