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
printenv | grep -E '^(ALPACA_|ANTHROPIC_|POLYGON_|TWITTER_|SLACK_|TZ|STATE_DIR|PATH|HOME)' > /etc/environment
chmod 644 /etc/environment

# Log startup
echo "[$(date -Iseconds)] Alpaca Trading Bot starting..."
echo "  TZ: ${TZ}"
echo "  Paper Trading: ${ALPACA_PAPER_TRADE:-True}"
echo "  Running tick.py as: botuser (non-root for Claude Code permissions)"

# Start cron in foreground
exec cron -f
