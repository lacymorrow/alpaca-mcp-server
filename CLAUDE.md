# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Model Context Protocol (MCP) server for Alpaca's Trading API, plus an **autonomous trading bot** that uses Claude Code to make trading decisions. It enables LLMs to interact with Alpaca's trading infrastructure for stock trading, options trading, crypto trading, portfolio management, watchlists, and market data.

## Current Project State (as of 2026-01-03)

**Phase 1 Implementation: COMPLETE & TESTED** - The core trading bot infrastructure has been built and verified:
- `scripts/tick.py` - Python tick script that invokes Claude Code CLI
- `mcp-config.json` - MCP server configuration for Claude Code
- `crontab` - Cron schedule for tick execution (uses `gosu botuser` for non-root execution)
- `templates/strategy.md` and `templates/plan.md` - Initial templates
- Updated `Dockerfile` with Claude Code CLI, cron, and non-root `botuser`
- Updated `docker-compose.yml` with trading-bot and mcp-server services
- Updated `.env.example` with all required variables

**Tested on 2026-01-03:** Docker build and tick execution verified working. Bot successfully connected to Alpaca, retrieved positions, and updated plan.md with market analysis.

## Development Commands

### Setup
```bash
# Create and activate virtual environment
python3 -m venv myvenv
source myvenv/bin/activate  # Windows: myvenv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the MCP Server (Standalone)
```bash
# Local usage (stdio transport - default)
python alpaca_mcp_server.py

# Remote usage (HTTP transport)
python alpaca_mcp_server.py --transport http --host 0.0.0.0 --port 8000
```

### Running the Trading Bot
```bash
# Build and run with Docker Compose
docker compose build
docker compose up trading-bot

# Run a single tick manually (for testing) - must use gosu for non-root execution
docker compose run --rm trading-bot gosu botuser /usr/local/bin/tick.py

# Run analysis-only tick (no trades)
docker compose run --rm trading-bot gosu botuser /usr/local/bin/tick.py --analysis-only

# View logs
docker compose exec trading-bot tail -f /data/alpaca-bot/logs/cron.log

# Check state files
docker compose run --rm trading-bot cat /data/alpaca-bot/state.json

# Start optional HTTP MCP server alongside bot
docker compose --profile mcp up
```

### Environment Variables
Copy `.env.example` to `.env` and configure:

| Variable | Required | Description |
|----------|----------|-------------|
| `ALPACA_API_KEY` | Yes | Alpaca API key |
| `ALPACA_SECRET_KEY` | Yes | Alpaca secret key |
| `ALPACA_PAPER_TRADE` | No | `True` (default) or `False` for live trading |
| `ANTHROPIC_API_KEY` | Yes | For Claude Code CLI (required for trading bot) |
| `POLYGON_API_KEY` | No | For Polygon.io news MCP server (optional) |
| `SLACK_WEBHOOK_URL` | No | For error alerts (optional but recommended) |
| `DEBUG` | No | Set to `True` for debug logging |

## Architecture

### MCP Server (`alpaca_mcp_server.py`)
Single-file MCP server using FastMCP. Exposes ~31 tools for trading operations.

**Alpaca Clients** (with `UserAgentMixin` for tracking):
- `TradingClientSigned` - Order execution, positions, account info
- `StockHistoricalDataClientSigned` - Stock market data
- `OptionHistoricalDataClientSigned` - Options data and Greeks
- `CorporateActionsClientSigned` - Dividends, splits, earnings
- `CryptoHistoricalDataClientSigned` - Crypto market data

**Tool Categories**:
- Account & Positions: `get_account_info`, `get_positions`, `close_position`
- Stock Data: `get_stock_quote`, `get_stock_bars`, `get_stock_snapshot`
- Orders: `get_orders`, `place_stock_order`, `cancel_order_by_id`
- Options: `get_option_contracts`, `place_option_market_order`
- Crypto: `place_crypto_order`
- Market Info: `get_market_clock`, `get_market_calendar`, `get_corporate_announcements`
- Watchlists & Assets: `create_watchlist`, `get_asset_info`, `get_all_assets`

### Trading Bot (`scripts/tick.py`)
Autonomous trading bot executed by cron every 15 minutes during market hours.

**Execution Flow**:
1. Load state from `/data/alpaca-bot/state.json`
2. Read `plan.md` and `strategy.md` for context
3. Assemble prompt with state, plan, strategy, recent actions
4. Invoke Claude Code CLI with MCP servers configured (`claude --print --mcp-config ...`)
5. Parse JSON response with trading decisions
6. Log decisions to `logs/actions.ndjson`
7. Update state.json with new positions/buying power
8. Send Slack alert on errors

**State Files** (in `/data/alpaca-bot/` - Docker volume):
| File | Purpose | Mutability |
|------|---------|------------|
| `state.json` | Current positions, buying power, action history (last 50) | Bot writes each tick |
| `plan.md` | Short-term trading plan | Bot can modify |
| `strategy.md` | Trading approach and rules | Bot can modify |
| `logs/actions.ndjson` | Append-only decision log | Bot appends |
| `logs/errors.ndjson` | Error log | Bot appends |
| `logs/cron.log` | Cron execution output | System appends |

**Cron Schedule** (America/New_York timezone):
- Market hours: Every 15 min, 9:30 AM - 4:00 PM ET, Mon-Fri
- Off-hours: Every 2 hours in analysis-only mode
- Weekends: Twice daily (10 AM, 6 PM) analysis

### Docker Configuration
- `Dockerfile` - Installs Claude Code CLI via npm, cron, Python deps, sets up entrypoint
- `docker-compose.yml` - Two services:
  - `trading-bot` - Cron-based autonomous trading (default)
  - `mcp-server` - HTTP MCP server (optional, use `--profile mcp`)
- `mcp-config.json` - MCP server configuration for Claude Code (uses env var substitution)
- `crontab` - Cron schedule for tick execution

### Helper Functions
Located in `alpaca_mcp_server.py`:
- `_parse_iso_datetime()` - Parses ISO datetime strings
- `_parse_date_ymd()` - Parses 'YYYY-MM-DD' format
- `_month_name_to_number()` - Converts month names to numbers

### Transport Configuration
MCP server supports:
- `stdio` (default) - For local MCP clients, used by trading bot
- `http` - For remote connections
- `sse` - Deprecated

## Key Design Decisions

These decisions were made during the interview process and should be understood for future work:

### Trading Strategy
- **Full Autonomy**: Bot has full control, no safety limits or circuit breakers
- **News/Event-Driven**: React to market-moving news, political events, key tweets
- **Political Volatility Awareness**: Current market environment has Trump/Musk causing significant swings
- **Self-Modifying**: Bot can edit its own `plan.md` and `strategy.md` files

### Technical Decisions
- **Per-Tick MCP Startup**: Claude Code manages MCP server lifecycle via stdio (vs. long-running server)
- **Prompt File Approach**: Full context (state, plan, strategy, history) assembled in tick.py
- **Python for Tick Script**: Better error handling and JSON parsing than bash
- **Model Selection**: Uses Opus by default, falls back to Sonnet when quota exhausted
- **No Fixed Position Limits**: Bot manages its own risk with available capital

### Error Handling
- Errors logged to `errors.ndjson`
- Slack webhook notification sent on errors
- Bot continues on next tick (cron handles scheduling)
- 5-minute timeout on Claude Code execution

### Slack Notifications
The bot sends two types of Slack notifications:

**Tick Summary** (after every successful tick):
- Portfolio value and P/L (color-coded: green/red/yellow)
- Buying power
- Trades executed (if any)
- Market status (open/closed)
- Top 3 positions by P/L
- Bot's notes

**Error Alert** (on failures):
- Error message
- Tick timestamp
- Last action taken

### Asset Types
- **Phase 1 (Current)**: Stocks only
- **Phase 2 (Future)**: Add crypto for 24/7 exposure
- **Phase 3 (Future)**: Add options for hedging and leverage

## File Structure

```
alpaca-mcp-server/
├── alpaca_mcp_server.py      # MCP server (31 trading tools)
├── scripts/
│   ├── tick.py               # Python tick script for Claude Code
│   └── alpaca-bot-tick.sh    # Legacy lash script (kept for future)
├── templates/
│   ├── strategy.md           # Initial strategy template
│   └── plan.md               # Initial plan template
├── mcp-config.json           # MCP server config for Claude Code
├── crontab                   # Cron schedule
├── Dockerfile                # Container with Claude Code + cron
├── docker-compose.yml        # Bot + optional MCP server
├── .env.example              # Environment variables template
├── .github/core/
│   └── user_agent_mixin.py   # User agent tracking
├── SPEC.md                   # Full specification document
├── CLAUDE.md                 # This file
└── README.md                 # Project readme
```

## Implementation Phases

### Phase 1: Core Trading Bot - COMPLETE & TESTED
- [x] Write `scripts/tick.py` in Python
- [x] Update Dockerfile with Claude Code CLI and cron
- [x] Create `mcp-config.json` with Alpaca server
- [x] Create initial `strategy.md` and `plan.md` templates
- [x] Set up Slack webhook alerting
- [x] Test Docker build and tick execution (verified 2026-01-03)
- [x] Bot runs as non-root `botuser` (required for `--dangerously-skip-permissions`)
- [ ] **NEXT: Validate with paper trading over 1 week** (currently running on live account)

### Phase 2: News Integration - COMPLETE
- [x] Add Polygon.io MCP server to mcp-config.json (official server from polygon-io/mcp_polygon)
- [x] Install `uvx` globally for running Polygon MCP server
- [x] Bot now has access to stock news, analyst ratings, earnings dates, market context
- [ ] Tune strategy for news-driven decisions (ongoing)

### Phase 3: Expand Asset Types
- [ ] Enable crypto trading (24/7 capability)
- [ ] Add options trading with appropriate strategy updates

### Phase 4: Long-term Memory (Future)
- [ ] Evaluate mem0 or SQLite-based memory MCP
- [ ] Implement summarization layer for historical context
- [ ] Add semantic search for past decisions

## Testing Checklist

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

## Important Notes for Continuing Work

1. **User's .env is configured for LIVE trading** (`ALPACA_PAPER_TRADE=False`) - be careful!

2. **mcp-config.json uses `${VAR}` syntax** - Claude Code should substitute these from environment at runtime. If not, may need to modify tick.py to do runtime substitution.

3. **Deployment target is Coolify** - User mentioned they use Coolify for builds from repo.

4. **No pause/intervention mechanism** - Bot runs continuously with no manual override system.

5. **Slack webhook URL is configured** - User has alerts set up.

6. **Polygon API key is set** - Ready for Phase 2 news integration.

## Reference Documentation

- Full specification: `SPEC.md`
- Alpaca API: https://docs.alpaca.markets/
- Claude Code CLI: https://claude.ai/code
- FastMCP: https://github.com/jlowin/fastmcp
