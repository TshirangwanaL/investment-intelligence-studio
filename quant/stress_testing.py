"""Portfolio stress testing — scenario library with impact estimation.

Includes a fixed scenario library (deterministic, auditable) plus
LLM-generated custom scenarios based on current market regime.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np
import pandas as pd

from schemas.portfolio import PortfolioState


@dataclass
class ScenarioDefinition:
    name: str
    description: str
    factor_shocks: dict[str, float]


SCENARIO_LIBRARY: list[ScenarioDefinition] = [
    ScenarioDefinition(
        name="Market Crash (-20%)",
        description="Broad equity drawdown of 20%",
        factor_shocks={"market": -0.20},
    ),
    ScenarioDefinition(
        name="Rates Shock (+200bp)",
        description="Sudden 200bp rise in rates; growth names hit harder",
        factor_shocks={"market": -0.08, "growth_tilt": -0.12, "value_tilt": -0.03},
    ),
    ScenarioDefinition(
        name="Oil/Energy Shock (+40%)",
        description="Energy prices spike 40%; energy names benefit, consumers hurt",
        factor_shocks={"market": -0.05, "energy_beta": 0.15, "consumer_beta": -0.10},
    ),
    ScenarioDefinition(
        name="Tech Sell-off (-25%)",
        description="Technology sector drawdown of 25%",
        factor_shocks={"market": -0.10, "tech_beta": -0.25},
    ),
    ScenarioDefinition(
        name="Stagflation",
        description="Rising inflation + slowing growth",
        factor_shocks={"market": -0.15, "value_tilt": -0.05, "growth_tilt": -0.20},
    ),
    ScenarioDefinition(
        name="Risk-Off Flight",
        description="Flight to quality: defensive names outperform",
        factor_shocks={"market": -0.12, "defensive_beta": 0.05, "high_beta": -0.20},
    ),
]

SECTOR_SENSITIVITY = {
    "Technology": {"tech_beta": 1.0, "growth_tilt": 0.7, "high_beta": 0.5},
    "Healthcare": {"defensive_beta": 0.6, "growth_tilt": 0.3},
    "Financials": {"value_tilt": 0.5, "high_beta": 0.4},
    "Energy": {"energy_beta": 1.0, "value_tilt": 0.4},
    "Consumer Discretionary": {"consumer_beta": 0.8, "growth_tilt": 0.4, "high_beta": 0.3},
    "Consumer Staples": {"defensive_beta": 0.8, "consumer_beta": 0.3},
    "Industrials": {"value_tilt": 0.3, "high_beta": 0.2},
    "Materials": {"value_tilt": 0.3, "energy_beta": 0.3},
    "Utilities": {"defensive_beta": 0.9},
    "Real Estate": {"value_tilt": 0.4, "defensive_beta": 0.3},
    "Communication Services": {"tech_beta": 0.5, "growth_tilt": 0.4},
}


@dataclass
class StressResult:
    scenario_name: str
    portfolio_impact_pct: float
    position_impacts: dict[str, float]
    top_contributors: list[tuple[str, float]]
    description: str


class StressTestEngine:
    @staticmethod
    def run_scenario(
        portfolio: PortfolioState,
        scenario: ScenarioDefinition,
    ) -> StressResult:
        position_impacts: dict[str, float] = {}

        for pos in portfolio.positions:
            sector = pos.sector or "Unknown"
            sensitivities = SECTOR_SENSITIVITY.get(sector, {})

            impact = scenario.factor_shocks.get("market", 0.0)

            for factor, shock in scenario.factor_shocks.items():
                if factor == "market":
                    continue
                sensitivity = sensitivities.get(factor, 0.0)
                impact += shock * sensitivity

            position_impacts[pos.ticker] = impact

        portfolio_impact = sum(
            pos.weight * position_impacts.get(pos.ticker, 0.0)
            for pos in portfolio.positions
        )

        contributions = [
            (pos.ticker, pos.weight * position_impacts.get(pos.ticker, 0.0))
            for pos in portfolio.positions
        ]
        contributions.sort(key=lambda x: x[1])
        top_contributors = contributions[:5]

        return StressResult(
            scenario_name=scenario.name,
            portfolio_impact_pct=portfolio_impact * 100,
            position_impacts={k: v * 100 for k, v in position_impacts.items()},
            top_contributors=[(t, v * 100) for t, v in top_contributors],
            description=scenario.description,
        )

    @classmethod
    def run_all_scenarios(
        cls,
        portfolio: PortfolioState,
        scenarios: list[ScenarioDefinition] | None = None,
    ) -> list[StressResult]:
        scenarios = scenarios or SCENARIO_LIBRARY
        return [cls.run_scenario(portfolio, s) for s in scenarios]


class ScenarioGenerator:
    """LLM-powered custom scenario generation based on current market regime.

    Generates scenarios ON TOP of the fixed library — the fixed library stays
    deterministic for reproducibility; these add contextual depth.
    """

    SYSTEM_PROMPT = """You are a risk strategist at a macro hedge fund.
Given the current market regime, portfolio composition, and recent news themes,
propose 2-3 custom stress scenarios that the standard library does NOT cover.

Each scenario must have:
- name: concise label (e.g. "China Property Contagion")
- description: 1-2 sentence explanation
- factor_shocks: dict mapping factor names to shock magnitudes (-1.0 to 1.0)

Valid factor names: market, growth_tilt, value_tilt, tech_beta, energy_beta,
consumer_beta, defensive_beta, high_beta

Return valid JSON: {"scenarios": [{"name": "...", "description": "...", "factor_shocks": {...}}, ...]}"""

    @staticmethod
    def generate(
        regime_context: dict[str, Any] | None = None,
        portfolio_tickers: list[str] | None = None,
        news_themes: list[str] | None = None,
    ) -> list[ScenarioDefinition]:
        """Generate custom scenarios using the LLM. Returns empty list on failure."""
        try:
            from config import settings

            prompt = f"""Current environment:
- Regime: {json.dumps(regime_context or {}, default=str)[:1500]}
- Portfolio tickers: {portfolio_tickers or []}
- Recent news themes: {news_themes or []}

Propose 2-3 custom stress scenarios tailored to this specific environment.
Return valid JSON only."""

            if settings.use_azure:
                from openai import AzureOpenAI
                client = AzureOpenAI(
                    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                    api_key=settings.AZURE_OPENAI_API_KEY,
                    api_version=settings.AZURE_OPENAI_API_VERSION,
                )
                model = settings.AZURE_OPENAI_DEPLOYMENT
            else:
                from openai import OpenAI
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                model = settings.LLM_MODEL

            kwargs: dict[str, Any] = {
                "model": model,
                "messages": [
                    {"role": "system", "content": ScenarioGenerator.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            }
            if not model.startswith("o"):
                kwargs["temperature"] = 0.4

            resp = client.chat.completions.create(**kwargs)
            raw = resp.choices[0].message.content or "{}"
            parsed = json.loads(raw)

            VALID_FACTORS = {
                "market", "growth_tilt", "value_tilt", "tech_beta",
                "energy_beta", "consumer_beta", "defensive_beta", "high_beta",
            }
            results = []
            for s in parsed.get("scenarios", []):
                shocks = {
                    k: max(-1.0, min(1.0, float(v)))
                    for k, v in s.get("factor_shocks", {}).items()
                    if k in VALID_FACTORS
                }
                if shocks:
                    results.append(ScenarioDefinition(
                        name=f"[AI] {s.get('name', 'Custom')}",
                        description=s.get("description", ""),
                        factor_shocks=shocks,
                    ))
            return results
        except Exception:
            return []
