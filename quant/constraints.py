"""Constraints engine — enforce investment policy limits and emit alerts."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from schemas.policy import ConstraintAlert, ConstraintRule, Policy, Severity
from schemas.portfolio import PortfolioState, TradePlan


class ConstraintsEngine:
    def __init__(self, policy: Optional[Policy] = None) -> None:
        self.policy = policy or Policy()

    def check_portfolio(self, portfolio: PortfolioState) -> list[ConstraintAlert]:
        alerts: list[ConstraintAlert] = []
        weights = [p.weight for p in portfolio.positions]

        for pos in portfolio.positions:
            if pos.weight > self.policy.max_position_weight:
                alerts.append(ConstraintAlert(
                    rule=ConstraintRule(
                        rule_id="max_position",
                        name="Max Position Weight",
                        parameter="weight",
                        threshold=self.policy.max_position_weight,
                        severity=Severity.CRITICAL,
                    ),
                    current_value=pos.weight,
                    message=f"{pos.ticker} weight {pos.weight:.1%} exceeds max {self.policy.max_position_weight:.1%}",
                ))

        if weights:
            sorted_w = sorted(weights, reverse=True)
            top5 = sum(sorted_w[:5])
            if top5 > self.policy.top5_max_concentration:
                alerts.append(ConstraintAlert(
                    rule=ConstraintRule(
                        rule_id="top5_concentration",
                        name="Top-5 Concentration",
                        parameter="top5_weight",
                        threshold=self.policy.top5_max_concentration,
                        severity=Severity.WARNING,
                    ),
                    current_value=top5,
                    message=f"Top-5 concentration {top5:.1%} exceeds {self.policy.top5_max_concentration:.1%}",
                ))

        sector_weights: dict[str, float] = {}
        for pos in portfolio.positions:
            s = pos.sector or "Unknown"
            sector_weights[s] = sector_weights.get(s, 0.0) + pos.weight
        for sector, sw in sector_weights.items():
            if sw > self.policy.sector_cap:
                alerts.append(ConstraintAlert(
                    rule=ConstraintRule(
                        rule_id=f"sector_cap_{sector}",
                        name=f"Sector Cap ({sector})",
                        parameter="sector_weight",
                        threshold=self.policy.sector_cap,
                        severity=Severity.WARNING,
                    ),
                    current_value=sw,
                    message=f"Sector '{sector}' weight {sw:.1%} exceeds cap {self.policy.sector_cap:.1%}",
                ))

        if portfolio.cash_weight < self.policy.cash_floor:
            alerts.append(ConstraintAlert(
                rule=ConstraintRule(
                    rule_id="cash_floor",
                    name="Cash Floor",
                    parameter="cash_weight",
                    threshold=self.policy.cash_floor,
                    severity=Severity.CRITICAL,
                ),
                current_value=portfolio.cash_weight,
                message=f"Cash {portfolio.cash_weight:.1%} below floor {self.policy.cash_floor:.1%}",
            ))

        n = len(portfolio.positions)
        if n < self.policy.min_positions:
            alerts.append(ConstraintAlert(
                rule=ConstraintRule(
                    rule_id="min_positions",
                    name="Min Positions",
                    parameter="position_count",
                    threshold=float(self.policy.min_positions),
                    severity=Severity.WARNING,
                ),
                current_value=float(n),
                message=f"Only {n} positions, minimum is {self.policy.min_positions}",
            ))
        if n > self.policy.max_positions:
            alerts.append(ConstraintAlert(
                rule=ConstraintRule(
                    rule_id="max_positions",
                    name="Max Positions",
                    parameter="position_count",
                    threshold=float(self.policy.max_positions),
                    severity=Severity.WARNING,
                ),
                current_value=float(n),
                message=f"{n} positions exceeds maximum {self.policy.max_positions}",
            ))

        return alerts

    def check_trade_plan(self, plan: TradePlan,
                         portfolio: PortfolioState) -> list[ConstraintAlert]:
        """Check a proposed trade plan against constraints.

        This applies the plan hypothetically and checks the resulting state.
        """
        alerts = self.check_portfolio(portfolio)

        if plan.total_turnover > self.policy.max_turnover_per_rebalance:
            alerts.append(ConstraintAlert(
                rule=ConstraintRule(
                    rule_id="max_turnover",
                    name="Max Turnover",
                    parameter="turnover",
                    threshold=self.policy.max_turnover_per_rebalance,
                    severity=Severity.WARNING,
                ),
                current_value=plan.total_turnover,
                message=f"Turnover {plan.total_turnover:.1%} exceeds max {self.policy.max_turnover_per_rebalance:.1%}",
            ))

        return alerts

    def has_critical_alerts(self, alerts: list[ConstraintAlert]) -> bool:
        return any(a.rule.severity == Severity.CRITICAL for a in alerts)
