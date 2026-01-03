FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    bash \
    curl \
    cron \
    jq \
    nodejs \
    npm \
    util-linux \
    tzdata \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Set timezone to Eastern Time
ENV TZ=America/New_York
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Create non-root user for running Claude Code (required for --dangerously-skip-permissions)
RUN useradd -m -s /bin/bash botuser

# Install lash CLI tool (kept for future use)
RUN curl -fsSL https://raw.githubusercontent.com/lacymorrow/lash/main/install | bash

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Install uv (Python package runner) for Polygon MCP server - install globally
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    cp /root/.local/bin/uv /usr/local/bin/ && \
    cp /root/.local/bin/uvx /usr/local/bin/ && \
    chmod 755 /usr/local/bin/uv /usr/local/bin/uvx

# Add lash to PATH
ENV PATH="/root/.lash/bin:$PATH"

# Copy application files
COPY . .

# Make app files readable by botuser
RUN chmod 644 /app/mcp-config.json && \
    chown -R root:botuser /app && \
    chmod -R g+r /app

# Install Python tick script
RUN install -m 0755 scripts/tick.py /usr/local/bin/tick.py

# Install legacy lash tick script (kept for future use)
RUN install -m 0755 scripts/alpaca-bot-tick.sh /usr/local/bin/alpaca-bot-tick.sh

# Install crontab
COPY crontab /etc/cron.d/alpaca-bot
RUN chmod 0644 /etc/cron.d/alpaca-bot
RUN crontab /etc/cron.d/alpaca-bot

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create data directories with proper ownership
RUN mkdir -p /data/alpaca-bot/logs && \
    chown -R botuser:botuser /data/alpaca-bot

# Copy template files for initial state
COPY templates/strategy.md /app/templates/strategy.md
COPY templates/plan.md /app/templates/plan.md

# Create entrypoint script
RUN cat > /app/entrypoint.sh << 'EOF'
#!/bin/bash
set -e

# Initialize state files if they don't exist (as root, then chown)
if [ ! -f /data/alpaca-bot/strategy.md ]; then
    cp /app/templates/strategy.md /data/alpaca-bot/strategy.md
    chown botuser:botuser /data/alpaca-bot/strategy.md
fi
if [ ! -f /data/alpaca-bot/plan.md ]; then
    cp /app/templates/plan.md /data/alpaca-bot/plan.md
    chown botuser:botuser /data/alpaca-bot/plan.md
fi

# Ensure data directory ownership
chown -R botuser:botuser /data/alpaca-bot

# Export environment variables for cron (make accessible to botuser)
printenv | grep -E '^(ALPACA_|ANTHROPIC_|POLYGON_|SLACK_|TZ|STATE_DIR|PATH|HOME)' > /etc/environment
chmod 644 /etc/environment

# Log startup
echo "[$(date -Iseconds)] Alpaca Trading Bot starting..."
echo "  TZ: ${TZ}"
echo "  Paper Trading: ${ALPACA_PAPER_TRADE:-True}"
echo "  Running tick.py as: botuser (non-root for Claude Code permissions)"

# Start cron in foreground
exec cron -f
EOF
RUN chmod +x /app/entrypoint.sh

# Default command starts the cron-based trading bot
# Override with docker-compose command to run MCP server directly
CMD ["/app/entrypoint.sh"]
