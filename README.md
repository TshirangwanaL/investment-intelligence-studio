# Investment Intelligence Studio

**Institutional-grade decision support for portfolio managers, equity research analysts, and risk teams.**

> This is a decision-support application, not an execution system. The default portfolio is a paper portfolio stored locally in SQLite. LLM agents produce analysis and proposals — only app-controlled commit functions may modify portfolio state after validation.

---

## Architecture Overview

```
├── app.py                    # Streamlit main entry
├── pages/                    # Streamlit multi-page app
│   ├── 1_Equity_Research.py
│   ├── 2_Portfolio_Manager.py
│   ├── 3_Market_News.py
│   └── 4_Audit_Trail.py
├── schemas/                  # Pydantic domain models
├── mcp_servers/              # MCP tool servers (data adapters)
│   ├── alpha_vantage.py      # Market data (OHLC, technicals)
│   ├── fred.py               # Macro / economic data
│   ├── sec_edgar.py          # SEC filings
│   ├── gdelt.py              # Global news / events
│   ├── fmp.py                # Earnings calendar & transcripts
│   └── quant_mcp.py          # Internal safe-compute quant server
├── quant/                    # Quantitative engine
│   ├── portfolio_metrics.py  # Vol, correlation, drawdown
│   ├── factor_model.py       # Fama-French factor regression
│   ├── stress_testing.py     # Scenario library
│   └── constraints.py        # Investment policy enforcement
├── agents/                   # LLM-powered agents
│   ├── market_narrative.py   # Regime + macro narrative
│   ├── equity_analyst.py     # Single-stock thesis
│   ├── risk_analytics.py     # Portfolio risk assessment
│   ├── asset_manager.py      # Rebalancing + trade plans
│   ├── decision_synthesizer.py # IC decision note
│   └── orchestrator.py       # Multi-agent workflow
├── governance/               # Governance controls
│   ├── autopilot.py          # Hybrid autopilot validator
│   └── drift_detection.py    # Thesis drift detection
├── persistence/              # SQLite persistence layer
│   ├── database.py           # Schema + CRUD
│   ├── audit_log.py          # Audit trail
│   └── thesis_store.py       # Thesis persistence
├── cache/                    # API response caching
├── tests/                    # Test suite
├── config.py                 # Centralised configuration
├── .env.example              # Environment variable template
└── requirements.txt          # Python dependencies
```

---

## Setup

### 1. Clone and install dependencies

```bash
cd Day9
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure API keys

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

Required keys:
- `OPENAI_API_KEY` — for LLM-based agents
- `ALPHAVANTAGE_API_KEY` — [Get free key](https://www.alphavantage.co/support/#api-key)
- `FRED_API_KEY` — [Get key](https://fred.stlouisfed.org/docs/api/api_key.html)
- `FMP_API_KEY` — [Get key](https://financialmodelingprep.com/developer/docs/)

### 3. Run the application

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`.

### 4. Run tests

```bash
pytest tests/ -v
```

---

## Data Sources

| Provider | Use | Rate Limits |
|----------|-----|-------------|
| **Alpha Vantage** | OHLC, technicals, company overview | 5 calls/min (free tier) |
| **FRED** | CPI, Fed Funds, unemployment, yield spreads | 120 calls/min |
| **SEC EDGAR** | Company filings, XBRL facts | 10 req/sec (fair access) |
| **GDELT** | Global news, tone analysis, event signals | ~60 calls/min |
| **Financial Modeling Prep** | Earnings calendar, transcripts | 10 calls/min (free) |
| **Kenneth French Library** | Fama-French factor data (3/5-factor) | Bulk download, cached locally |

---

## MCP Tool Servers

Each MCP server is a Python class with strict boundaries:

- **Read-only access** to external APIs
- **Input validation** on all parameters
- **Rate limiting** with exponential backoff
- **Structured JSON** responses with metadata (source, timestamp, query params)
- **Caching** (in-memory TTL + disk-based)
- **Audit logging** — every tool call is recorded

### Running MCP servers

MCP servers are instantiated by the agents automatically. They are not standalone processes — they're Python objects wired into agents with strict scope enforcement.

---

## Governance Model

### Why LLM Cannot Execute Writes

1. **Agents produce proposals** (TradePlan) — they never directly modify portfolio state
2. **Autopilot validator** classifies actions into AUTO (safe) and REVIEW (needs approval) buckets
3. **Commit functions** are app-controlled and only execute after validation passes
4. **Kill switch** immediately halts all automated actions
5. **Audit trail** records every decision, tool call, and PM rationale

### Hybrid Autopilot Rules

**AUTO** (applied automatically) — must satisfy ALL:
- `|weight_delta| ≤ 1.5%` per asset
- No new positions
- No full exits
- Turnover ≤ 5% per rebalance
- Confidence ≥ 70%
- No high-risk news (litigation, fraud, bankruptcy, regulatory)
- All constraints pass

**REVIEW** (requires PM approval) — triggered by ANY:
- New position or full exit
- `weight_delta > 2%`
- Turnover > 5%
- Confidence < 70%
- High-risk news detected
- Missing/stale data or tool failures
- Any constraint violation

---

## Rate Limiting & Caching

- **In-memory cache**: TTL-based (default 1 hour), up to 2048 entries
- **Disk cache**: JSON files in `data/cache/`, keyed by SHA-256 of request signature
- **Rate limiters**: Per-server token bucket; Alpha Vantage limited to 5/min
- **Retry**: Exponential backoff (3 attempts) on network errors via `tenacity`

---

## Key Features

- **Factor Exposure Analysis** — FF3/FF5 regression on portfolio returns
- **Concentration Risk Engine** — Max position, top-5, sector caps, cash floor, turnover limits
- **Earnings Call Intelligence** — Transcript extraction, tone analysis, guidance signals
- **Macro Regime Detection** — FRED-based regime classification
- **Portfolio Stress Testing** — 6 pre-built scenarios (market crash, rates shock, etc.)
- **Thesis Drift Detection** — Periodic re-check of thesis claims against new data
- **Investment Committee Mode** — Multi-agent debate with vote (buy/hold/sell)
- **Catalyst Calendar** — Earnings + macro events for watchlist
