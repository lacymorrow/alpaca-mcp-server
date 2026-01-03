#!/usr/bin/env python3
"""
Alpaca Trading Bot Tick Script

Executed by cron every 15 minutes during market hours.
Invokes Claude Code CLI with MCP servers to make autonomous trading decisions.
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import urllib.request
import urllib.error

# Configuration
STATE_DIR = Path(os.getenv("STATE_DIR", "/data/alpaca-bot"))
LOG_DIR = STATE_DIR / "logs"
STATE_JSON = STATE_DIR / "state.json"
PLAN_MD = STATE_DIR / "plan.md"
STRATEGY_MD = STATE_DIR / "strategy.md"
ACTIONS_LOG = LOG_DIR / "actions.ndjson"
ERRORS_LOG = LOG_DIR / "errors.ndjson"

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
TZ = os.getenv("TZ", "America/New_York")

# MCP config location
MCP_CONFIG = Path("/app/mcp-config.json")


def ensure_directories():
    """Create required directories if they don't exist."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def init_state_json():
    """Initialize state.json if it doesn't exist."""
    if not STATE_JSON.exists():
        initial_state = {
            "last_tick_iso": None,
            "positions_snapshot": [],
            "buying_power": None,
            "actions_history": [],
            "notes": "Initial state. Human can add notes here."
        }
        STATE_JSON.write_text(json.dumps(initial_state, indent=2))
    return json.loads(STATE_JSON.read_text())


def init_plan_md():
    """Initialize plan.md if it doesn't exist."""
    if not PLAN_MD.exists():
        PLAN_MD.write_text("""# Trading Plan

## Current Objectives
- Evaluate market conditions each tick
- Look for news-driven opportunities
- Manage existing positions

## Recent Observations
(Bot will update this section)

## Next Actions
(Bot will update this section)
""")
    return PLAN_MD.read_text()


def init_strategy_md():
    """Initialize strategy.md if it doesn't exist."""
    if not STRATEGY_MD.exists():
        STRATEGY_MD.write_text("""# Trading Strategy

## Approach
- Event-driven trading focused on news catalysts
- Monitor political developments (executive orders, policy changes, key tweets)
- Look for asymmetric risk/reward setups
- React quickly to market-moving news

## Current Market Context
- High volatility environment due to political uncertainty
- Policy changes can cause rapid sector rotations
- Social media (especially tweets from key figures) can move markets

## Position Management
- No fixed position count limit
- Size positions based on conviction and volatility
- Consider correlation between positions
- Manage overall portfolio heat, not individual position limits

## Decision Framework
1. What is the catalyst? (news, earnings, policy, sentiment shift)
2. What is the expected move? (direction, magnitude, timeframe)
3. What invalidates the thesis?
4. Risk/reward ratio assessment

## Entry Criteria
- Clear catalyst identified
- Favorable risk/reward (target > 2:1 when possible)
- Sufficient liquidity
- Not chasing extended moves

## Exit Criteria
- Target reached
- Thesis invalidated
- Better opportunity elsewhere
- Risk management (trailing stops, time stops)

## Evolution Log
This strategy will evolve based on what works. Document learnings below:

---
(Bot will append learnings here)
""")
    return STRATEGY_MD.read_text()


def get_recent_actions(state: dict, count: int = 10) -> list:
    """Get the most recent actions from history."""
    history = state.get("actions_history", [])
    return history[-count:] if history else []


def build_prompt(state: dict, plan: str, strategy: str, analysis_only: bool = False) -> str:
    """Assemble the prompt for Claude Code."""
    now = datetime.now().isoformat()
    recent_actions = get_recent_actions(state, 10)

    mode_instruction = ""
    if analysis_only:
        mode_instruction = """
NOTE: This is an ANALYSIS-ONLY tick (market is likely closed).
- Do NOT place any orders
- Review positions and P/L
- Update plan.md with observations
- Prepare for next trading session
"""

    prompt = f"""CURRENT STATE:
{json.dumps(state, indent=2)}

TRADING PLAN:
{plan}

STRATEGY:
{strategy}

RECENT ACTIONS (last 10):
{json.dumps(recent_actions, indent=2)}

CURRENT TIME: {now} ({TZ})
{mode_instruction}

INSTRUCTIONS:
You are an autonomous trading bot with full control of this Alpaca account.

1. First, call get_market_clock to check if market is open
2. Call get_account_info and get_positions to understand current state
3. Search for relevant news that could affect your positions or create opportunities
4. Make trading decisions based on your strategy and current conditions
5. You may update plan.md and strategy.md if your approach evolves
6. Execute trades using place_stock_order when you have conviction

If market is closed, perform analysis only - do not place orders.

After completing your analysis and any trades, respond with a JSON block in this format:
```json
{{
  "decisions": [
    {{"action": "buy|sell|close|none", "symbol": "TICKER", "qty": 10, "type": "market|limit", "limit_price": null, "reasoning": "why"}}
  ],
  "positions_snapshot": [
    {{"symbol": "TICKER", "qty": 10, "market_value": 1000.00, "unrealized_pl": 50.00}}
  ],
  "buying_power": 10000.00,
  "market_open": true,
  "notes": "brief summary of this tick",
  "plan_updated": false,
  "strategy_updated": false
}}
```
"""
    return prompt


def send_slack_alert(error: str, tick_time: str, last_action: Optional[dict] = None):
    """Send error alert to Slack webhook."""
    if not SLACK_WEBHOOK_URL:
        print(f"[WARN] No SLACK_WEBHOOK_URL configured, skipping alert", file=sys.stderr)
        return

    payload = {
        "text": ":x: Alpaca Trading Bot Error",
        "attachments": [{
            "color": "danger",
            "fields": [
                {"title": "Error", "value": str(error)[:500], "short": False},
                {"title": "Tick Time", "value": tick_time, "short": True},
                {"title": "Last Action", "value": json.dumps(last_action)[:200] if last_action else "None", "short": True}
            ]
        }]
    }

    try:
        req = urllib.request.Request(
            SLACK_WEBHOOK_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req, timeout=10)
        print(f"[INFO] Slack alert sent")
    except Exception as e:
        print(f"[ERROR] Failed to send Slack alert: {e}", file=sys.stderr)


def send_slack_summary(tick_time: str, result: dict, analysis_only: bool = False):
    """Send tick summary to Slack webhook."""
    if not SLACK_WEBHOOK_URL:
        return

    # Calculate portfolio totals
    positions = result.get("positions_snapshot", [])
    total_value = sum(p.get("market_value", 0) for p in positions)
    total_pl = sum(p.get("unrealized_pl", 0) for p in positions)
    buying_power = result.get("buying_power", 0) or 0

    # Format P/L with sign and color
    pl_sign = "+" if total_pl >= 0 else ""
    pl_pct = (total_pl / (total_value - total_pl) * 100) if (total_value - total_pl) > 0 else 0

    # Build decisions summary
    decisions = result.get("decisions", [])
    trades = [d for d in decisions if d.get("action") not in ["none", None]]

    if trades:
        trade_lines = []
        for t in trades[:5]:  # Limit to 5 trades
            action = t.get("action", "?").upper()
            symbol = t.get("symbol", "?")
            qty = t.get("qty", "?")
            trade_lines.append(f"{action} {qty}x {symbol}")
        trades_text = "\n".join(trade_lines)
    else:
        trades_text = "No trades executed"

    # Build positions summary (top 3 by P/L)
    sorted_positions = sorted(positions, key=lambda p: abs(p.get("unrealized_pl", 0)), reverse=True)
    pos_lines = []
    for p in sorted_positions[:3]:
        symbol = p.get("symbol", "?")
        pl = p.get("unrealized_pl", 0)
        pl_sign_pos = "+" if pl >= 0 else ""
        pos_lines.append(f"{symbol}: {pl_sign_pos}${pl:.2f}")
    positions_text = " | ".join(pos_lines) if pos_lines else "No positions"

    # Determine color based on P/L
    if total_pl > 0:
        color = "good"  # green
    elif total_pl < 0:
        color = "danger"  # red
    else:
        color = "warning"  # yellow

    # Market status
    market_status = ":chart_with_upwards_trend: Market Open" if result.get("market_open") else ":moon: Market Closed"
    mode = " (Analysis Only)" if analysis_only else ""

    # Build payload
    payload = {
        "text": f":robot_face: Trading Bot Tick Complete{mode}",
        "attachments": [{
            "color": color,
            "fields": [
                {
                    "title": "Portfolio",
                    "value": f"${total_value:.2f} ({pl_sign}${total_pl:.2f} / {pl_sign}{pl_pct:.1f}%)",
                    "short": True
                },
                {
                    "title": "Buying Power",
                    "value": f"${buying_power:.2f}",
                    "short": True
                },
                {
                    "title": "Trades",
                    "value": trades_text,
                    "short": True
                },
                {
                    "title": "Status",
                    "value": market_status,
                    "short": True
                },
                {
                    "title": "Top Positions",
                    "value": positions_text,
                    "short": False
                },
                {
                    "title": "Notes",
                    "value": result.get("notes", "No notes")[:300],
                    "short": False
                }
            ],
            "footer": f"Tick: {tick_time}",
            "ts": int(datetime.fromisoformat(tick_time).timestamp())
        }]
    }

    try:
        req = urllib.request.Request(
            SLACK_WEBHOOK_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req, timeout=10)
        print(f"[INFO] Slack summary sent")
    except Exception as e:
        print(f"[ERROR] Failed to send Slack summary: {e}", file=sys.stderr)


def log_error(error: str, tick_time: str):
    """Log error to errors.ndjson."""
    entry = {
        "ts": tick_time,
        "error": str(error),
        "type": type(error).__name__ if isinstance(error, Exception) else "Error"
    }
    with open(ERRORS_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def log_action(tick_time: str, result: dict):
    """Log action to actions.ndjson."""
    entry = {
        "ts": tick_time,
        **result
    }
    with open(ACTIONS_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def parse_claude_response(output: str) -> dict:
    """Extract JSON block from Claude's response."""
    import re

    # Try to find fenced JSON block
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', output, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
    else:
        # Try to find raw JSON object
        match = re.search(r'\{[\s\S]*\}', output)
        if match:
            json_str = match.group(0)
        else:
            # Return a default structure with the raw output
            return {
                "decisions": [],
                "notes": "Could not parse JSON from response",
                "raw_output": output[:2000],
                "parse_error": True
            }

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        return {
            "decisions": [],
            "notes": f"JSON parse error: {e}",
            "raw_output": output[:2000],
            "parse_error": True
        }


def run_claude_code(prompt: str) -> tuple[str, int]:
    """Execute Claude Code CLI with the prompt."""

    # Build command
    cmd = [
        "claude",
        "--print",  # Non-interactive, output to stdout
        "--output-format", "text",  # Plain text output
        "--dangerously-skip-permissions",  # Required for autonomous operation (must run as non-root)
    ]

    # Add MCP config if it exists
    if MCP_CONFIG.exists():
        cmd.extend(["--mcp-config", str(MCP_CONFIG)])

    # Add prompt
    cmd.extend(["-p", prompt])

    # Set up environment
    env = os.environ.copy()
    env["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY", "")

    print(f"[INFO] Executing Claude Code...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            env=env,
            cwd="/app"
        )

        if result.returncode != 0:
            print(f"[WARN] Claude Code exited with code {result.returncode}", file=sys.stderr)
            if result.stderr:
                print(f"[STDERR] {result.stderr[:1000]}", file=sys.stderr)

        return result.stdout, result.returncode

    except subprocess.TimeoutExpired:
        raise Exception("Claude Code timed out after 5 minutes")
    except FileNotFoundError:
        raise Exception("Claude Code CLI not found. Is it installed?")


def update_state(state: dict, result: dict, tick_time: str) -> dict:
    """Update state.json with new data from tick."""

    # Update basic fields
    state["last_tick_iso"] = tick_time

    # Update positions if provided
    if "positions_snapshot" in result:
        state["positions_snapshot"] = result["positions_snapshot"]

    # Update buying power if provided
    if "buying_power" in result:
        state["buying_power"] = result["buying_power"]

    # Append to actions history (keep last 50)
    action_entry = {
        "ts": tick_time,
        "decisions": result.get("decisions", []),
        "market_open": result.get("market_open"),
        "notes": result.get("notes", "")
    }

    history = state.get("actions_history", [])
    history.append(action_entry)
    state["actions_history"] = history[-50:]  # Keep last 50

    return state


def main():
    """Main tick execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Alpaca Trading Bot Tick")
    parser.add_argument("--analysis-only", action="store_true",
                        help="Run in analysis-only mode (no trades)")
    args = parser.parse_args()

    tick_time = datetime.now().isoformat()
    print(f"[{tick_time}] Starting tick...")

    try:
        # Initialize directories and files
        ensure_directories()
        state = init_state_json()
        plan = init_plan_md()
        strategy = init_strategy_md()

        # Build prompt
        prompt = build_prompt(state, plan, strategy, analysis_only=args.analysis_only)

        # Run Claude Code
        output, returncode = run_claude_code(prompt)

        # Parse response
        result = parse_claude_response(output)

        # Log the action
        log_action(tick_time, result)

        # Update state
        state = update_state(state, result, tick_time)
        STATE_JSON.write_text(json.dumps(state, indent=2))

        # Check for parse errors
        if result.get("parse_error"):
            print(f"[WARN] Could not parse Claude response as JSON", file=sys.stderr)

        # Print summary
        decisions = result.get("decisions", [])
        print(f"[{tick_time}] Tick complete. Decisions: {len(decisions)}")
        for d in decisions:
            print(f"  - {d.get('action', 'unknown')} {d.get('symbol', '?')} x{d.get('qty', '?')}: {d.get('reasoning', '')[:50]}")

        if result.get("notes"):
            print(f"  Notes: {result['notes'][:100]}")

        # Send Slack summary notification
        send_slack_summary(tick_time, result, analysis_only=args.analysis_only)

    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] {error_msg}", file=sys.stderr)

        # Log error
        log_error(e, tick_time)

        # Send Slack alert
        last_action = None
        try:
            state = json.loads(STATE_JSON.read_text())
            history = state.get("actions_history", [])
            last_action = history[-1] if history else None
        except:
            pass

        send_slack_alert(error_msg, tick_time, last_action)

        # Exit with error code (but don't crash cron)
        sys.exit(1)


if __name__ == "__main__":
    main()
