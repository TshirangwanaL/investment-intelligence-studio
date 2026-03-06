# Investment Intelligence Studio — 5-Minute Presentation

## Strategy: Use the Audit Trail page as your technical backbone. It already shows everything — architecture, agents, MCP, governance. Walk through it live while explaining how the app works.

---

## MINUTE 1: Hook + What This Is (60 seconds)

**Say:**

> "I built an AI-powered investment research terminal. Think of it as having a team of five specialist analysts — a market strategist, an equity analyst, a risk manager, an asset manager, and a committee chair — all available on demand, working from real market data, with every single action audited."

> "It's important to understand: this is decision support, not a trading bot. The AI analyses, recommends, and debates — but a human always has the final say. The LLM never writes to the portfolio directly."

**Show:** Open the app. Show the main sidebar briefly (4 pages, data source status indicators).

---

## MINUTE 2: Architecture via Audit Trail (60 seconds)

**Open the Audit Trail page. Go to the "LLM Usage Map" tab.**

**Say:**

> "Let me show you how this is built by looking at the audit trail. This tab separates the system into two categories: LLM-powered modules and deterministic modules."

> "On the LLM side, I have 9 agents — market narrative, equity analyst, risk analytics, asset manager, decision synthesizer, and others. Each one has a specific job and can only access specific data sources. The equity analyst can pull stock prices, earnings, and SEC filings, but it can't touch the quant engine. The risk agent can use the quant engine but can't access the news server. This is strict scope enforcement."

> "On the deterministic side — and this is critical — the actual maths never touches the LLM. Portfolio metrics like volatility, VaR, and Sharpe ratio are pure statistical calculations. The Fama-French factor regression is a standard OLS regression. The constraints engine and autopilot validator are rule-based. I made this split deliberately: maths and governance must be exact and reproducible, so they stay deterministic."

---

## MINUTE 3: MCP + Data Flow via Audit Trail (60 seconds)

**Switch to the "MCP Servers" tab. Click "Discover all tools".**

**Say:**

> "This is the MCP layer — Model Context Protocol. Every data source is wrapped in a server with defined tools. Click discover and you can see every tool across all 6 servers with their schemas."

> "Each server enforces read-only access, validates inputs with Pydantic, rate-limits requests, caches responses, and logs every call. For data, I use yfinance for stock prices, earnings, news, and dividends — it's free and needs no API key. FRED gives me macro data like CPI and the Fed Funds rate. SEC EDGAR gives me company filings. The Kenneth French Library gives me the Fama-French factor data for regression analysis."

**Switch to the "Tool Calls" tab.**

> "Here you can see every tool call that's been made — which server, which tool, latency, success/failure, and whether it was served from cache. This is full observability."

---

## MINUTE 4: Live Demo — The Key Features (60 seconds)

**Quick-fire through 3 features. Don't deep-dive, just show and move.**

**1. Equity Research page — Scenario Tests tab (15 sec)**

> "I can type any scenario — 'What if interest rates rise 200 basis points?' — and the AI gives me a structured impact analysis: stock price effect, probability, transmission channels, what to watch for. I can also ask follow-up questions."

**2. Portfolio Manager — Factor Exposures tab (20 sec)**

> "This runs a Fama-French regression on my portfolio. The actual returns come from stock prices via yfinance, and the factor returns come from the Kenneth French academic dataset. You can see the regression line, how the portfolio moves relative to the market, and what the factors can't explain — that's your stock-specific risk."

**3. Portfolio Manager — Investment Committee tab (25 sec)**

> "This is the interactive debate room. I ask any investment question and the right committee member answers automatically — macro questions go to the Market Strategist, risk questions go to the Risk Manager. It's a real back-and-forth conversation with my full portfolio context included."

*Type a quick question like "What's the biggest risk in my portfolio?" and show the response.*

---

## MINUTE 5: Governance + Wrap-up (60 seconds)

**Go back to Audit Trail — "Timeline" tab.**

**Say:**

> "Every action in the system is recorded here — agent outputs, trade approvals, trade rejections, policy changes. This is institutional memory. If an auditor asks 'why did you make this trade?', the answer is here with the full agent reasoning and my rationale."

**Switch to the "Agent Outputs" tab briefly.**

> "You can drill into any agent's output and see the exact JSON it produced."

**Wrap up:**

> "The governance model is simple: agents propose, humans decide. There are three autopilot modes — full manual where I approve everything, hybrid where small safe changes auto-apply but large ones need my click, and full auto with a kill switch. The kill switch is a single toggle that halts all automated actions immediately."

> "The tech stack is Python, Streamlit for the UI, Azure OpenAI o4-mini for the LLM, Pydantic for all data validation, SQLite for persistence and audit, and the Fama-French library for factor analysis. All of this runs locally."

---

## If They Ask Questions

**"Why not use a real frontend like React?"**
> "Streamlit let me move fast — it's Python-native and handles state. For production I'd use React with FastAPI, but for a research prototype this was the right trade-off."

**"How do you prevent hallucinated financial data?"**
> "The LLM never invents market data. All numbers come through MCP servers from yfinance, FRED, and SEC EDGAR. The LLM only interprets data it receives. Thesis claims are stored and re-checked against new data via drift detection."

**"What is MCP?"**
> "Model Context Protocol — a pattern where each data source is wrapped in a server with input validation, rate limiting, structured responses, and audit logging. Agents interact with data through this controlled interface, not raw API calls."

**"Why Fama-French?"**
> "CAPM uses one factor — market beta. Fama-French 3-factor adds size and value, which explains about 90% of diversified portfolio return variation. The 5-factor model adds profitability and investment. It's the academic standard for institutional factor attribution."

**"What does the kill switch do?"**
> "Sets autopilot to full manual mode. Every action requires explicit human approval. Nothing automated runs."

**"How do you handle LLM token limits?"**
> "I compact JSON payloads before sending to the LLM and set max_completion_tokens explicitly. For Azure's o-series models, this parameter is different from standard max_tokens — getting it wrong causes silent truncation."

---

## Demo Flow Cheat Sheet (if you want to rehearse)

1. Open app → sidebar (30 sec)
2. Audit Trail → LLM Usage Map tab (45 sec)
3. Audit Trail → MCP Servers tab → Discover tools (45 sec)
4. Audit Trail → Tool Calls tab (15 sec)
5. Equity Research → Scenario Tests → Run a preset (15 sec)
6. Portfolio Manager → Factor Exposures → Show regression charts (20 sec)
7. Portfolio Manager → Investment Committee → Ask a question (25 sec)
8. Audit Trail → Timeline tab (30 sec)
9. Wrap up governance + tech stack (15 sec)
