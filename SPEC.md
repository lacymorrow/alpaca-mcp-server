# Alpaca Trading Bot Specification

## Current Implementation Status (2026-01-03)

**Phase 1: COMPLETE & TESTED** - Core infrastructure built and verified working.
**Phase 2: COMPLETE** - Polygon.io news integration added.

| Component | Status | Notes |
|-----------|--------|-------|
| `scripts/tick.py` | ✅ Done | Python tick script with Claude Code CLI, Slack summaries |
| `mcp-config.json` | ✅ Done | Alpaca + Polygon.io servers configured |
| `crontab` | ✅ Done | Full schedule with `gosu botuser` for non-root execution |
| `templates/` | ✅ Done | `strategy.md` and `plan.md` templates |
| `Dockerfile` | ✅ Done | Claude Code CLI + cron + uv + non-root botuser |
| `docker-compose.yml` | ✅ Done | trading-bot (default) + mcp-server (optional) |
| `.env.example` | ✅ Done | All required variables documented |
| Docker build test | ✅ Passed | Verified 2026-01-03 |
| Tick execution test | ✅ Passed | Bot connected to Alpaca, retrieved positions, updated plan |
| Polygon.io integration | ✅ Done | News, analyst ratings, earnings dates available |
| Slack notifications | ✅ Done | Summary after each tick + error alerts |

**Next Steps:**
1. Phase 3: Enable crypto trading (24/7 capability)
2. Phase 4: Add options trading
3. Phase 5: Long-term memory (mem0 or SQLite)

---

## Overview

Autonomous trading bot using Claude Code CLI with the Alpaca MCP server, deployed via Docker on Coolify. The bot operates on a 15-minute tick cycle during market hours, making trading decisions based on news, events, and market conditions.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Container                        │
│                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │   Cron      │───▶│  tick.py     │───▶│  Claude Code  │  │
│  │  (crond)    │    │  (Python)    │    │     CLI       │  │
│  └─────────────┘    └──────────────┘    └───────┬───────┘  │
│                                                  │          │
│                     ┌────────────────────────────┘          │
│                     ▼                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              MCP Servers (stdio)                     │   │
│  │  ┌─────────────┐ ┌──────────┐ ┌─────────────────┐   │   │
│  │  │   Alpaca    │ │ Polygon  │ │  Twitter/Nitter │   │   │
│  │  │  (trading)  │ │  (news)  │ │    (social)     │   │   │
│  │  └─────────────┘ └──────────┘ └─────────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Persistent State (/data)                │   │
│  │  state.json │ plan.md │ strategy.md │ logs/         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Tick Script (`scripts/tick.py`)

Python script executed by cron every 15 minutes during market hours.

**Responsibilities:**
- Load state from `/data/alpaca-bot/state.json`
- Check market status via `get_market_clock` tool
- Assemble context (state, plan, strategy, recent history)
- Invoke Claude Code CLI with MCP servers configured
- Parse Claude's response and log decisions
- Update state files
- Send Slack alerts on errors

**Invocation:**
```bash
claude --print \
  --mcp-config /app/mcp-config.json \
  -p "$(cat /data/alpaca-bot/prompt.txt)"
```

### 2. State Management

**Location:** `/data/alpaca-bot/` (mounted volume in Coolify)

| File | Purpose | Mutability |
|------|---------|------------|
| `state.json` | Current positions, last tick, action history | Bot writes each tick |
| `plan.md` | Short-term trading plan | Bot can modify |
| `strategy.md` | Trading approach and rules | Bot can modify |
| `logs/actions.ndjson` | Append-only decision log | Bot appends |
| `logs/errors.ndjson` | Error log for alerting | Bot appends |

**state.json schema:**
```json
{
  "last_tick_iso": "2025-01-03T10:30:00-05:00",
  "positions_snapshot": [...],
  "buying_power": 10000.00,
  "actions_history": [/* last 50 actions */],
  "notes": "Human-editable notes field"
}
```

### 3. MCP Server Configuration

**File:** `/app/mcp-config.json`

```json
{
  "mcpServers": {
    "alpaca": {
      "command": "python",
      "args": ["/app/alpaca_mcp_server.py"],
      "env": {
        "ALPACA_API_KEY": "${ALPACA_API_KEY}",
        "ALPACA_SECRET_KEY": "${ALPACA_SECRET_KEY}",
        "ALPACA_PAPER_TRADE": "${ALPACA_PAPER_TRADE:-True}"
      }
    },
    "polygon": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/polygon-io/mcp_polygon@0.1.1", "mcp_polygon"],
      "env": {
        "POLYGON_API_KEY": "${POLYGON_API_KEY}"
      }
    }
  }
}
```

**Tool Access:**
- Alpaca: Full access to all 31 trading tools
- Polygon.io: 35+ tools for stocks, options, forex, crypto data, news, earnings, analyst ratings

### 4. Cron Schedule

**Timezone:** America/New_York (ET)

```cron
# Market hours: every 15 minutes, 9:30 AM - 4:00 PM ET, Mon-Fri
*/15 9-15 * * 1-5 /usr/local/bin/tick.py
30 9 * * 1-5 /usr/local/bin/tick.py
0,15,30,45 16 * * 1-5 /usr/local/bin/tick.py

# Off-hours analysis: every 2 hours
0 */2 * * * /usr/local/bin/tick.py --analysis-only
```

## Trading Strategy

### Philosophy

The bot has **full autonomy** with an aggressive news-driven approach. No training wheels.

- **News/Event-Driven:** React to market-moving news with tiered urgency
- **Political Volatility Awareness:** Trump/Musk causing significant market swings
- **No Fixed Limits:** Bot manages its own risk with available capital
- **No Circuit Breakers:** Trust Claude's judgment in all market conditions

### News Catalyst Tiers

| Tier | Action | Examples |
|------|--------|----------|
| **Tier 1** | Act immediately, size up to 25% | Earnings surprises >10%, FDA approvals, M&A, executive orders |
| **Tier 2** | Act within session, 10-15% | Analyst upgrades, insider buying >$1M, guidance changes |
| **Tier 3** | Monitor & position, 5% max | Industry trends, macro data, political rhetoric |

### News Freshness Rules

- **< 1 hour old**: Full signal strength, act aggressively
- **1-4 hours old**: Reduced signal, check if already priced in
- **> 4 hours old**: Likely priced in, only act if market hasn't reacted
- **> 24 hours old**: Ignore unless follow-up developments

### Sentiment Scoring (-3 to +3)

- **+3**: Transformational positive (acquisition at premium, FDA approval)
- **+2**: Strong positive (earnings beat, upgrade)
- **+1**: Mild positive (minor contract, positive mention)
- **0**: Neutral/noise
- **-1**: Mild negative (minor miss, cautious analyst)
- **-2**: Strong negative (earnings miss, downgrade, investigation)
- **-3**: Catastrophic (fraud, bankruptcy, product failure)

### Tick Workflow (4 Phases)

1. **Market & Account Status**: `get_market_clock`, `get_account_info`, `get_positions`
2. **News Gathering**: `list_ticker_news` for positions, watchlist, sector ETFs
3. **Analysis & Decision**: Score news, identify catalyst tier, apply framework
4. **Execution**: Trade with conviction, update plan.md, evolve strategy.md

### Watchlist

- **Mega caps**: AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA
- **Crypto proxies**: COIN, MARA, MSTR, RIOT
- **Political plays**: Defense (LMT, RTX), Energy (XOM, CVX), Banks (JPM, GS)
- **Sector ETFs**: SPY, QQQ, XLF, XLE, XLK

See `templates/strategy.md` for full strategy with position sizing, risk controls, and sector sensitivity matrix.

### Asset Types

**Phase 1 (Current):** Stocks only
- All stock trading tools enabled
- Options and crypto tools available but discouraged initially

**Future Phases:**
- Phase 2: Add crypto for 24/7 exposure
- Phase 3: Add options for hedging and leverage

## Market Hours Behavior

### During Market Hours (9:30 AM - 4:00 PM ET)
- Full trading capability
- Place market, limit, stop orders
- Manage positions actively
- React to real-time news

### Outside Market Hours
- **Analysis only mode** - no trade execution
- Review positions and P/L
- Update plan.md with overnight analysis
- Process news and prepare for next session
- No order placement (queuing not implemented)

## Error Handling

### On Error:
1. Log error to `/data/alpaca-bot/logs/errors.ndjson`
2. Send Slack webhook notification
3. Exit cleanly (cron will invoke next tick)

### Slack Alert Format:
```json
{
  "text": "Alpaca Bot Error",
  "attachments": [{
    "color": "danger",
    "fields": [
      {"title": "Error", "value": "...", "short": false},
      {"title": "Tick", "value": "2025-01-03T10:30:00-05:00", "short": true},
      {"title": "Last Action", "value": "...", "short": true}
    ]
  }]
}
```

## Logging

### Granularity: Standard (decisions + reasoning)

Each tick logs to `actions.ndjson`:
```json
{
  "ts": "2025-01-03T10:30:00-05:00",
  "market_open": true,
  "decisions": [
    {
      "action": "buy",
      "symbol": "NVDA",
      "qty": 10,
      "type": "market",
      "reasoning": "Post-CES momentum, AI chip demand catalyst"
    }
  ],
  "tools_called": ["get_account_info", "get_stock_quote", "place_stock_order"],
  "plan_updated": false,
  "strategy_updated": false
}
```

## News & Data Sources

### Built-in (Claude Code)
- Web search via Claude's native capability
- Used for breaking news, tweet lookups, general research

### Polygon.io MCP Server
- Ticker-specific news
- SEC filings
- Earnings announcements
- Requires `POLYGON_API_KEY` env var

### Twitter/X via Nitter (Future)
- Monitor @elonmusk, @realDonaldTrump, financial accounts
- No API key required (scraping)
- Add as separate MCP server when available

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ALPACA_API_KEY` | Yes | Alpaca API key |
| `ALPACA_SECRET_KEY` | Yes | Alpaca secret key |
| `ALPACA_PAPER_TRADE` | No | `True` (default) or `False` for live |
| `ANTHROPIC_API_KEY` | Yes | For Claude Code CLI |
| `POLYGON_API_KEY` | No | For Polygon news MCP server |
| `SLACK_WEBHOOK_URL` | No | For error alerts |
| `TZ` | No | Defaults to `America/New_York` |

## Docker Configuration

### Dockerfile Key Components

```dockerfile
# Base image
FROM python:3.13-slim

# System dependencies including gosu for user switching
RUN apt-get update && apt-get install -y \
    bash curl cron jq nodejs npm util-linux tzdata gosu

# Create non-root user (required for --dangerously-skip-permissions)
RUN useradd -m -s /bin/bash botuser

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Install uv (Python package runner) for Polygon MCP server
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    cp /root/.local/bin/uv /usr/local/bin/ && \
    cp /root/.local/bin/uvx /usr/local/bin/

# Copy and configure crontab (uses gosu botuser)
COPY crontab /etc/cron.d/alpaca-bot

# Create data directories with proper ownership
RUN mkdir -p /data/alpaca-bot/logs && \
    chown -R botuser:botuser /data/alpaca-bot

# Entrypoint initializes state files and starts cron
CMD ["/app/entrypoint.sh"]
```

### Key Design Decisions
- **Non-root execution**: `botuser` required for `--dangerously-skip-permissions`
- **gosu**: Used in crontab to switch from root cron to botuser
- **uvx**: Installed globally so botuser can run Polygon MCP server
- **Entrypoint**: Initializes templates, sets permissions, exports env vars for cron

### docker-compose.yml

```yaml
services:
  trading-bot:
    build: .
    environment:
      - ALPACA_API_KEY=${ALPACA_API_KEY}
      - ALPACA_SECRET_KEY=${ALPACA_SECRET_KEY}
      - ALPACA_PAPER_TRADE=${ALPACA_PAPER_TRADE:-True}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - POLYGON_API_KEY=${POLYGON_API_KEY:-}
      - SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL:-}
      - TZ=America/New_York
    volumes:
      - bot-data:/data/alpaca-bot
    restart: unless-stopped

  # Optional: HTTP MCP server (use --profile mcp to start)
  mcp-server:
    build: .
    profiles: [mcp]
    command: python alpaca_mcp_server.py --transport http --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    environment:
      - ALPACA_API_KEY=${ALPACA_API_KEY}
      - ALPACA_SECRET_KEY=${ALPACA_SECRET_KEY}
      - ALPACA_PAPER_TRADE=${ALPACA_PAPER_TRADE:-True}

volumes:
  bot-data:
```

## Claude Code Configuration

### Model Selection
- Uses Opus by default (max subscription)
- Automatically falls back to Sonnet when Opus quota exhausted
- No explicit model flag needed

### Context Assembly

The tick script assembles a prompt file:

```
CURRENT STATE:
<contents of state.json>

TRADING PLAN:
<contents of plan.md>

STRATEGY:
<contents of strategy.md>

RECENT ACTIONS (last 10):
<extracted from state.json>

CURRENT TIME: 2025-01-03T10:30:00-05:00 (America/New_York)
MARKET STATUS: [will be determined by get_market_clock]

INSTRUCTIONS:
You are an autonomous trading bot with full control of this Alpaca account.
- First, call get_market_clock to check if market is open
- Call get_account_info and get_positions to understand current state
- Search for relevant news using web search
- Make trading decisions based on your strategy and current conditions
- You may update plan.md and strategy.md if your approach evolves
- Log your reasoning for all decisions

If market is closed, perform analysis only. Do not place orders.

Respond with a JSON block containing your decisions and reasoning.
```

## File Structure (Final)

```
alpaca-mcp-server/
├── alpaca_mcp_server.py      # MCP server (existing)
├── Dockerfile                 # Updated with Claude Code + cron
├── docker-compose.yml         # Updated for bot deployment
├── mcp-config.json           # MCP server configuration for Claude
├── crontab                   # Cron schedule file
├── requirements.txt          # Python deps (existing)
├── scripts/
│   ├── tick.py              # Main tick script (Python)
│   └── alpaca-bot-tick.sh   # Legacy lash script (kept for future)
├── CLAUDE.md                 # Claude Code guidance (existing)
├── SPEC.md                   # This specification
└── README.md                 # Project readme (existing)
```

## Implementation Phases

### Phase 1: Core Trading Bot ✅ COMPLETE
1. ✅ Write `scripts/tick.py` in Python
2. ✅ Update Dockerfile with Claude Code CLI and cron
3. ✅ Create `mcp-config.json` with Alpaca server
4. ✅ Create initial `strategy.md` template
5. ✅ Set up Slack webhook alerting (error alerts + tick summaries)
6. ✅ Add non-root `botuser` for `--dangerously-skip-permissions`
7. ✅ Test Docker build and tick execution

### Phase 2: News Integration ✅ COMPLETE
1. ✅ Add Polygon.io MCP server (official: polygon-io/mcp_polygon)
2. ✅ Install `uvx` globally for running Polygon MCP
3. ✅ Bot has access to news, analyst ratings, earnings dates
4. ✅ Tuned strategy for news-driven decisions (2026-01-03)
   - Tiered catalyst system (Tier 1/2/3)
   - News freshness rules (<1hr, 1-4hr, >4hr)
   - Sentiment scoring (-3 to +3)
   - 4-phase tick workflow with explicit Polygon tool usage
   - Enhanced plan.md template with news radar

### Phase 3: Expand Asset Types (PLANNED)
1. Enable crypto trading (24/7 capability)
2. Add options trading with appropriate strategy updates

### Phase 4: Long-term Memory (Future)
1. Evaluate mem0 or SQLite-based memory MCP
2. Implement summarization layer for historical context
3. Add semantic search for past decisions

## Testing

### Paper Trading Validation
1. Deploy with `ALPACA_PAPER_TRADE=True`
2. Run for 1 week minimum
3. Review all decisions in `actions.ndjson`
4. Verify strategy evolution in `strategy.md`
5. Check error handling and Slack alerts

### Go-Live Checklist
- [ ] Paper trading validated
- [ ] `ALPACA_PAPER_TRADE=False` set
- [ ] Live API keys configured
- [ ] Slack alerts verified
- [ ] Coolify health checks configured
- [ ] Data volume backup configured
