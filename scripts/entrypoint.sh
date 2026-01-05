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

# Export environment variables for cron
# Cron doesn't read /etc/environment, so we inject vars directly into the crontab
ENV_FILE=/tmp/cron_env

# Explicitly list required environment variables (more robust than grep patterns)
REQUIRED_VARS=(
    # Alpaca credentials
    ALPACA_API_KEY
    ALPACA_SECRET_KEY
    ALPACA_PAPER_TRADE
    # Claude/Anthropic
    ANTHROPIC_API_KEY
    # Data providers
    POLYGON_API_KEY
    # Twitter
    TWITTER_API_KEY
    TWITTER_API_SECRET
    TWITTER_ACCESS_TOKEN
    TWITTER_ACCESS_TOKEN_SECRET
    # Notifications
    SLACK_WEBHOOK_URL
    # Asset type configuration
    ENABLE_STOCK_TRADING
    ENABLE_CRYPTO_TRADING
    ENABLE_OPTIONS_TRADING
    # System
    TZ
    STATE_DIR
    DEBUG
)

# Write each variable to env file if it's set
> "$ENV_FILE"
for var in "${REQUIRED_VARS[@]}"; do
    if [ -n "${!var+x}" ]; then
        echo "${var}=${!var}" >> "$ENV_FILE"
    fi
done

# Build a new crontab with environment variables at the top
{
    echo "SHELL=/bin/bash"
    echo "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/root/.local/bin"
    echo "HOME=/home/botuser"
    # Add all required env vars
    cat "$ENV_FILE"
    echo ""
    # Add the schedule lines (skip the header from original crontab)
    grep -E '^[0-9*]' /etc/cron.d/alpaca-bot
} > /tmp/crontab_with_env

# Install as root's crontab
crontab /tmp/crontab_with_env
rm -f "$ENV_FILE" /tmp/crontab_with_env

echo "  Crontab installed with environment variables"

# Show weekend schedule for verification
echo "  Weekend schedule (Sat/Sun):"
crontab -l | grep '0,6' || echo "    (none found)"

# Log startup
echo "[$(date -Iseconds)] Alpaca Trading Bot starting..."
echo "  TZ: ${TZ}"
echo "  Paper Trading: ${ALPACA_PAPER_TRADE:-True}"
echo "  Running tick.py as: botuser (non-root for Claude Code permissions)"

# Start cron in foreground
exec cron -f
