# Trading Strategy

## Core Philosophy
Aggressive news-driven trading. We move fast, size big on high-conviction plays, and aren't afraid to take concentrated positions. No hand-holding, no training wheels.

## News Integration (Polygon MCP)

### Every Tick Workflow
1. **Check positions first** - Use `list_ticker_news` for each held symbol
2. **Scan sector news** - Check news for sector ETFs (XLF, XLE, XLK, etc.) to spot rotations
3. **Hunt for opportunities** - Check news on watchlist tickers and trending names

### News Catalyst Tiers

**TIER 1 - Act Immediately (size up)**
- Earnings surprises (beat/miss by >10%)
- FDA approvals/rejections
- Major M&A announcements
- Executive orders directly affecting a company/sector
- Bankruptcy filings or debt restructuring
- Major contract wins (government, enterprise)

**TIER 2 - Act Within Session**
- Analyst upgrades/downgrades from major firms
- Insider buying >$1M
- Guidance changes
- Product launches with clear revenue impact
- Regulatory investigations announced
- Key executive departures (CEO, CFO)

**TIER 3 - Monitor & Position**
- Industry trend pieces
- Macro economic data (CPI, jobs, Fed)
- Political rhetoric without immediate action
- Competitor news that indirectly affects holdings

### News Freshness Rules
- **< 1 hour old**: Full signal strength, act aggressively
- **1-4 hours old**: Reduced signal, check if already priced in
- **> 4 hours old**: Likely priced in, only act if market hasn't reacted
- **> 24 hours old**: Ignore unless follow-up developments

### Sentiment Scoring
When evaluating news, assign a score from -3 to +3:
- **+3**: Transformational positive (acquisition at premium, FDA approval)
- **+2**: Strong positive (earnings beat, upgrade)
- **+1**: Mild positive (minor contract, positive mention)
- **0**: Neutral/noise
- **-1**: Mild negative (minor miss, cautious analyst)
- **-2**: Strong negative (earnings miss, downgrade, investigation)
- **-3**: Catastrophic (fraud, bankruptcy, product failure)

## Political & Macro Awareness

### Key Figures to Monitor (via news)
- Trump administration policy announcements
- Musk tweets/statements affecting Tesla, SpaceX suppliers, crypto
- Fed officials (Powell, governors) on rate policy
- SEC chair on crypto/regulatory actions

### Sector Sensitivity Matrix
| Event Type | Long Candidates | Short Candidates |
|------------|-----------------|------------------|
| Tariff threats | Domestic manufacturers | Importers, retailers |
| Deregulation talk | Banks, energy, crypto | Clean energy |
| Rate cut signals | Growth tech, REITs | Banks, insurers |
| Defense spending | LMT, RTX, NOC, GD | - |
| Crypto-friendly news | COIN, MARA, MSTR | - |

## Position Management

### Sizing Rules
- **High conviction (Tier 1 news)**: Up to 25% of portfolio
- **Medium conviction (Tier 2)**: 10-15% of portfolio
- **Speculative (Tier 3)**: 5% max
- **Never exceed 40% in single sector** unless thesis is sector-wide

### Correlation Awareness
- If holding multiple tech names, treat as single larger position
- Diversify across: Growth, Value, Cyclical, Defensive
- In high-vol environments, reduce gross exposure

## Decision Framework

For every trade, answer:
1. **Catalyst**: What specific news/event? How fresh?
2. **Magnitude**: What's the expected move? (%, $)
3. **Timeframe**: Intraday, swing (days), position (weeks)?
4. **Invalidation**: At what price/event is the thesis dead?
5. **R/R Ratio**: Risk $ vs Reward $ (want 2:1 minimum)

## Entry Criteria
- Tier 1 or Tier 2 news catalyst identified
- News is < 4 hours old OR market hasn't reacted
- Favorable risk/reward (2:1 minimum)
- Have a clear exit plan BEFORE entering
- Not chasing >5% intraday move (unless Tier 1)

## Exit Criteria
- Target hit (take profits, don't get greedy)
- Thesis invalidated by new information
- Time stop: If move hasn't happened in expected timeframe
- Better opportunity requires capital reallocation
- Sentiment score shifts (new contradicting news)

## Order Types

### When to Use Market Orders
- Tier 1 news, need immediate execution
- Highly liquid names (>1M daily volume)
- Exiting losing positions fast

### When to Use Limit Orders
- Tier 2/3 setups with less urgency
- Illiquid names
- Scaling into positions
- Taking profits at targets

## Watchlist (Check News Each Tick)
Maintain awareness of these high-news-flow names:
- **Mega caps**: AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA
- **Crypto proxies**: COIN, MARA, MSTR, RIOT
- **Political plays**: Defense (LMT, RTX), Energy (XOM, CVX), Banks (JPM, GS)
- **Volatility names**: GME, AMC (meme momentum)
- **Current holdings**: Always check news first

## Risk Controls

### Portfolio Heat
- Track total unrealized P/L as % of portfolio
- If down >5% on day, reduce position sizes
- If down >10%, go to cash and reassess

### Per-Position Limits
- No single position >30% of portfolio (except during brief Tier 1 plays)
- Cut losses at -10% unless thesis still intact with new supporting info

## Evolution Log
Document what's working and what's not. Adapt the strategy based on results.

---
### Learnings
(Bot will append learnings here as it trades)
