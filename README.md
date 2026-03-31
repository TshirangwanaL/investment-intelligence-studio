# Investment Intelligence Studio

AI-powered investment decision-support platform for equity research, portfolio analysis, and risk monitoring.

> This is a decision-support application, not a trade execution system.  
> LLM agents generate analysis and proposals, while portfolio changes are only applied through app-controlled commit functions after validation.

## What it does

Investment Intelligence Studio combines external market and macro data, quantitative analytics, and constrained LLM workflows into a single research environment.

Core capabilities include:
- equity research support using filings, market data, and news
- portfolio risk analysis using quantitative metrics and factor models
- market narrative generation using macro and event signals
- governance-controlled proposal workflows with validation and audit logging

Data adapters → Quant engine → Specialist agents → Decision synthesizer → Governance validator → App-controlled commit

  ## Why this project matters

This project was designed to explore how LLM-based systems can support investment workflows without replacing deterministic analytics or governance controls.

The goal is not automated trading. The goal is to improve research quality, portfolio oversight, and decision support by combining:
- structured external data access
- quantitative analytics
- constrained agent workflows
- validation and auditability

## System design

The platform is built around four layers:

1. **Data layer**  
   Modular data adapters retrieve market, macro, filings, earnings, and news data from external sources.

2. **Quant layer**  
   Quantitative modules compute portfolio metrics, factor exposures, stress tests, and policy checks.

3. **Agent layer**  
   Constrained LLM agents generate stock theses, market narratives, portfolio assessments, and decision notes.

4. **Governance layer**  
   Validation, audit logging, and controlled write paths ensure proposals are reviewed before portfolio state is changed.

## Example workflow

A typical workflow looks like this:

- market and macro data are pulled through external adapters
- quant modules compute portfolio and factor analytics
- specialist agents generate research and risk outputs
- a synthesizer produces a structured decision note
- governance checks validate whether the proposed action can proceed
- only app-controlled functions may commit approved changes

## Key engineering decisions

### 1. Agents do not write directly
LLM agents can analyse data and propose actions, but they cannot directly modify portfolio state. This reduces execution risk and keeps control with the application layer.

### 2. Data access is modular
Each external source is wrapped in a dedicated adapter, which improves maintainability and makes provider changes easier to handle.

### 3. Quant and LLM responsibilities are separated
Quantitative calculations are handled by deterministic Python modules, while LLMs are used for synthesis, explanation, and structured decision support.

### 4. Reliability is designed in
The system uses validation, caching, logging, and governance checks to improve consistency and traceability.

## Architecture overview
---

## End-to-end capabilities

### Equity research
- pull company and market context
- review filings and earnings context
- generate a structured stock thesis

### Portfolio analysis
- calculate volatility, drawdown, and concentration metrics
- evaluate factor exposures using Fama-French models
- assess portfolio-level risk and policy alignment

### Market intelligence
- combine macro indicators and event/news signals
- generate a market regime narrative
- surface risks relevant to positioning

### Governance and control
- classify proposed actions for review
- maintain audit trails for tool usage and decisions
- restrict portfolio changes to validated application paths
---

## Setup

### 1. Clone and install dependencies

```bash
cd investment-intelligence-studio
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
