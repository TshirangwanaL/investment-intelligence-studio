"""Multi-agent orchestrator — Investment Committee interaction loop.

Implements the prescribed interaction flow:
1. Market Narrative Agent → regime assessment
2. Equity Analyst Agent → thesis for each ticker
3. Asset Manager challenges Equity Analyst (stress test)
4. Equity Analyst responds with scenario outputs
5. Risk Analytics Agent → portfolio risk update
6. Asset Manager → trade plan
7. Decision Synthesizer → final note + vote
"""

from __future__ import annotations

import json
from typing import Any

from agents.market_narrative import MarketNarrativeAgent
from agents.equity_analyst import EquityAnalystAgent
from agents.risk_analytics import RiskAnalyticsAgent
from agents.asset_manager import AssetManagerAgent
from agents.decision_synthesizer import DecisionSynthesizerAgent

from mcp_servers.alpha_vantage import AlphaVantageMCP
from mcp_servers.fred import FredMCP
from mcp_servers.sec_edgar import SecEdgarMCP
from mcp_servers.gdelt import GdeltMCP
from mcp_servers.fmp import FMPMCP
from mcp_servers.quant_mcp import QuantMCP


def _wire_agents() -> dict[str, Any]:
    """Instantiate agents and wire MCP tools with strict scope enforcement."""
    av = AlphaVantageMCP()
    fred = FredMCP()
    edgar = SecEdgarMCP()
    gdelt = GdeltMCP()
    fmp = FMPMCP()
    quant = QuantMCP()

    market = MarketNarrativeAgent()
    market.register_tool("mcp_news_gdelt", gdelt)
    market.register_tool("mcp_macro_fred", fred)
    market.register_tool("mcp_marketdata_alpha_vantage", av)

    equity = EquityAnalystAgent()
    equity.register_tool("mcp_marketdata_alpha_vantage", av)
    equity.register_tool("mcp_events_fmp", fmp)
    equity.register_tool("mcp_filings_sec_edgar", edgar)
    equity.register_tool("mcp_news_gdelt", gdelt)

    risk = RiskAnalyticsAgent()
    risk.register_tool("mcp_quant", quant)
    risk.register_tool("mcp_marketdata_alpha_vantage", av)
    risk.register_tool("mcp_macro_fred", fred)

    manager = AssetManagerAgent()
    manager.register_tool("mcp_quant", quant)
    manager.register_tool("mcp_marketdata_alpha_vantage", av)
    manager.register_tool("mcp_news_gdelt", gdelt)
    manager.register_tool("mcp_macro_fred", fred)

    synthesizer = DecisionSynthesizerAgent()

    return {
        "market": market,
        "equity": equity,
        "risk": risk,
        "manager": manager,
        "synthesizer": synthesizer,
    }


def run_investment_committee(
    tickers: list[str],
    portfolio: dict,
    policy: dict | None = None,
    challenge: str = "Stress test under risk-off regime with rates rising 200bp",
    progress_callback: Any = None,
) -> dict[str, Any]:
    """Execute the full investment committee workflow.

    Returns a dict with all agent outputs and the debate transcript.
    """
    agents = _wire_agents()
    debate_log: list[dict] = []

    def _progress(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)

    _progress("Step 1/7: Market Narrative Agent assessing regime...")
    market_output = agents["market"].run({})
    debate_log.append({"agent": "market_narrative", "output": market_output})

    _progress("Step 2/7: Equity Analyst generating theses...")
    equity_outputs: dict[str, Any] = {}
    for ticker in tickers:
        thesis = agents["equity"].run({"ticker": ticker})
        equity_outputs[ticker] = thesis
        debate_log.append({"agent": "equity_analyst", "ticker": ticker, "output": thesis})

    _progress("Step 3/7: Asset Manager challenging Equity Analyst...")
    debate_log.append({
        "agent": "asset_manager",
        "type": "challenge",
        "message": challenge,
    })

    _progress("Step 4/7: Equity Analyst responding to challenge...")
    for ticker in tickers:
        scenario_response = agents["equity"].run({
            "ticker": ticker,
            "scenario_request": challenge,
        })
        equity_outputs[f"{ticker}_scenario"] = scenario_response
        debate_log.append({
            "agent": "equity_analyst",
            "ticker": ticker,
            "type": "scenario_response",
            "output": scenario_response,
        })

    _progress("Step 5/7: Risk Analytics Agent updating portfolio risk...")
    risk_output = agents["risk"].run({
        "portfolio": portfolio,
        "market_context": market_output,
    })
    debate_log.append({"agent": "risk_analytics", "output": risk_output})

    _progress("Step 6/7: Asset Manager producing trade plan...")
    trade_plan = agents["manager"].run({
        "portfolio": portfolio,
        "risk_assessment": risk_output,
        "equity_theses": equity_outputs,
        "market_context": market_output,
        "policy": policy or {},
    })
    debate_log.append({"agent": "asset_manager", "output": trade_plan})

    _progress("Step 7/7: Decision Synthesizer producing final note...")
    synthesis = agents["synthesizer"].run({
        "market_narrative": market_output,
        "equity_thesis": equity_outputs,
        "risk_assessment": risk_output,
        "trade_plan": trade_plan,
        "debate_log": debate_log,
    })
    debate_log.append({"agent": "decision_synthesizer", "output": synthesis})

    return {
        "market_narrative": market_output,
        "equity_theses": equity_outputs,
        "risk_assessment": risk_output,
        "trade_plan": trade_plan,
        "synthesis": synthesis,
        "debate_log": debate_log,
    }
