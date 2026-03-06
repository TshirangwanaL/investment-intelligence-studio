"""Tests for the constraints engine."""

import pytest

from schemas.portfolio import PortfolioState, Position, TradePlan, TradeAction, ActionType
from schemas.policy import Policy, Severity
from quant.constraints import ConstraintsEngine


def _make_portfolio(positions: list[tuple[str, float, str]], cash: float = 0.0) -> PortfolioState:
    return PortfolioState(
        positions=[
            Position(ticker=t, weight=w, sector=s) for t, w, s in positions
        ],
        cash_weight=cash,
    )


class TestConstraintsEngine:
    def test_max_position_weight_violation(self):
        policy = Policy(max_position_weight=0.10)
        engine = ConstraintsEngine(policy)
        portfolio = _make_portfolio([
            ("AAPL", 0.15, "Technology"),
            ("MSFT", 0.08, "Technology"),
        ], cash=0.77)

        alerts = engine.check_portfolio(portfolio)
        critical = [a for a in alerts if a.rule.rule_id == "max_position"]
        assert len(critical) == 1
        assert "AAPL" in critical[0].message

    def test_max_position_weight_passes(self):
        policy = Policy(max_position_weight=0.20)
        engine = ConstraintsEngine(policy)
        portfolio = _make_portfolio([
            ("AAPL", 0.15, "Technology"),
            ("MSFT", 0.08, "Technology"),
        ], cash=0.77)

        alerts = engine.check_portfolio(portfolio)
        position_alerts = [a for a in alerts if a.rule.rule_id == "max_position"]
        assert len(position_alerts) == 0

    def test_top5_concentration_violation(self):
        policy = Policy(top5_max_concentration=0.40)
        engine = ConstraintsEngine(policy)
        portfolio = _make_portfolio([
            ("A", 0.12, "Tech"),
            ("B", 0.10, "Tech"),
            ("C", 0.09, "Health"),
            ("D", 0.08, "Fin"),
            ("E", 0.07, "Energy"),
            ("F", 0.04, "Other"),
        ], cash=0.50)

        alerts = engine.check_portfolio(portfolio)
        top5_alerts = [a for a in alerts if a.rule.rule_id == "top5_concentration"]
        assert len(top5_alerts) == 1

    def test_sector_cap_violation(self):
        policy = Policy(sector_cap=0.25)
        engine = ConstraintsEngine(policy)
        portfolio = _make_portfolio([
            ("AAPL", 0.15, "Technology"),
            ("MSFT", 0.12, "Technology"),
            ("JNJ", 0.05, "Healthcare"),
        ], cash=0.68)

        alerts = engine.check_portfolio(portfolio)
        sector_alerts = [a for a in alerts if "sector_cap" in a.rule.rule_id]
        assert len(sector_alerts) == 1
        assert "Technology" in sector_alerts[0].message

    def test_cash_floor_violation(self):
        policy = Policy(cash_floor=0.05)
        engine = ConstraintsEngine(policy)
        portfolio = _make_portfolio([
            ("AAPL", 0.50, "Technology"),
            ("MSFT", 0.48, "Technology"),
        ], cash=0.02)

        alerts = engine.check_portfolio(portfolio)
        cash_alerts = [a for a in alerts if a.rule.rule_id == "cash_floor"]
        assert len(cash_alerts) == 1
        assert cash_alerts[0].rule.severity == Severity.CRITICAL

    def test_min_positions_violation(self):
        policy = Policy(min_positions=5)
        engine = ConstraintsEngine(policy)
        portfolio = _make_portfolio([
            ("AAPL", 0.30, "Technology"),
            ("MSFT", 0.20, "Technology"),
        ], cash=0.50)

        alerts = engine.check_portfolio(portfolio)
        min_alerts = [a for a in alerts if a.rule.rule_id == "min_positions"]
        assert len(min_alerts) == 1

    def test_turnover_violation(self):
        policy = Policy(max_turnover_per_rebalance=0.10)
        engine = ConstraintsEngine(policy)
        portfolio = _make_portfolio([("AAPL", 0.50, "Tech")], cash=0.50)
        plan = TradePlan(
            actions=[
                TradeAction(ticker="AAPL", action=ActionType.SELL,
                            weight_delta=-0.20, target_weight=0.30),
            ],
            total_turnover=0.20,
        )

        alerts = engine.check_trade_plan(plan, portfolio)
        turnover_alerts = [a for a in alerts if a.rule.rule_id == "max_turnover"]
        assert len(turnover_alerts) == 1

    def test_has_critical_alerts(self):
        policy = Policy(max_position_weight=0.10, cash_floor=0.05)
        engine = ConstraintsEngine(policy)
        portfolio = _make_portfolio([
            ("AAPL", 0.15, "Technology"),
        ], cash=0.02)

        alerts = engine.check_portfolio(portfolio)
        assert engine.has_critical_alerts(alerts)

    def test_clean_portfolio_passes(self):
        policy = Policy(
            max_position_weight=0.15,
            top5_max_concentration=0.60,
            sector_cap=0.30,
            cash_floor=0.02,
            min_positions=3,
        )
        engine = ConstraintsEngine(policy)
        portfolio = _make_portfolio([
            ("AAPL", 0.10, "Technology"),
            ("JNJ", 0.08, "Healthcare"),
            ("JPM", 0.08, "Financials"),
            ("XOM", 0.07, "Energy"),
            ("PG", 0.06, "Consumer Staples"),
        ], cash=0.61)

        alerts = engine.check_portfolio(portfolio)
        assert len(alerts) == 0
