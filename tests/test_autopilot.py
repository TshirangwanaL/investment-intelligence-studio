"""Tests for the hybrid autopilot validator."""

import pytest

from schemas.portfolio import TradePlan, TradeAction, ActionType, BucketType
from schemas.policy import Policy, AutopilotThresholds
from governance.autopilot import AutopilotValidator, AutopilotMode


def _make_action(**kwargs) -> TradeAction:
    defaults = {
        "ticker": "AAPL",
        "action": ActionType.REBALANCE,
        "current_weight": 0.10,
        "target_weight": 0.11,
        "weight_delta": 0.01,
        "confidence": 0.80,
        "is_new_position": False,
        "is_full_exit": False,
        "news_risk_flags": [],
    }
    defaults.update(kwargs)
    return TradeAction(**defaults)


def _make_plan(actions: list[TradeAction], turnover: float = 0.03) -> TradePlan:
    return TradePlan(actions=actions, total_turnover=turnover)


class TestAutopilotClassification:
    def test_safe_action_classified_as_auto(self):
        validator = AutopilotValidator()
        action = _make_action(weight_delta=0.01, confidence=0.85)
        plan = _make_plan([action], turnover=0.02)
        bucket = validator.classify_action(action, plan)
        assert bucket == BucketType.AUTO

    def test_new_position_classified_as_review(self):
        validator = AutopilotValidator()
        action = _make_action(is_new_position=True)
        plan = _make_plan([action])
        bucket = validator.classify_action(action, plan)
        assert bucket == BucketType.REVIEW

    def test_full_exit_classified_as_review(self):
        validator = AutopilotValidator()
        action = _make_action(is_full_exit=True)
        plan = _make_plan([action])
        bucket = validator.classify_action(action, plan)
        assert bucket == BucketType.REVIEW

    def test_large_weight_delta_classified_as_review(self):
        validator = AutopilotValidator()
        action = _make_action(weight_delta=0.03)
        plan = _make_plan([action])
        bucket = validator.classify_action(action, plan)
        assert bucket == BucketType.REVIEW

    def test_low_confidence_classified_as_review(self):
        validator = AutopilotValidator()
        action = _make_action(confidence=0.50)
        plan = _make_plan([action])
        bucket = validator.classify_action(action, plan)
        assert bucket == BucketType.REVIEW

    def test_high_risk_news_classified_as_review(self):
        validator = AutopilotValidator()
        action = _make_action(news_risk_flags=["litigation"])
        plan = _make_plan([action])
        bucket = validator.classify_action(action, plan)
        assert bucket == BucketType.REVIEW

    def test_high_turnover_classified_as_review(self):
        validator = AutopilotValidator()
        action = _make_action(weight_delta=0.01, confidence=0.85)
        plan = _make_plan([action], turnover=0.08)
        bucket = validator.classify_action(action, plan)
        assert bucket == BucketType.REVIEW

    def test_full_manual_mode_all_review(self):
        validator = AutopilotValidator()
        safe_action = _make_action(weight_delta=0.005, confidence=0.90)
        plan = _make_plan([safe_action], turnover=0.01)
        result = validator.classify_plan(plan, AutopilotMode.FULL_MANUAL)
        assert len(result.auto_actions) == 0
        assert len(result.review_actions) == 1

    def test_full_auto_mode_all_auto(self):
        validator = AutopilotValidator()
        risky_action = _make_action(is_new_position=True)
        plan = _make_plan([risky_action])
        result = validator.classify_plan(plan, AutopilotMode.FULL_AUTO)
        assert len(result.auto_actions) == 1
        assert len(result.review_actions) == 0

    def test_hybrid_mode_mixed(self):
        validator = AutopilotValidator()
        safe = _make_action(ticker="AAPL", weight_delta=0.005, confidence=0.90)
        risky = _make_action(ticker="NEW", is_new_position=True)
        plan = _make_plan([safe, risky], turnover=0.03)
        result = validator.classify_plan(plan, AutopilotMode.HYBRID)
        assert len(result.auto_actions) == 1
        assert len(result.review_actions) == 1
        assert result.auto_actions[0].ticker == "AAPL"
        assert result.review_actions[0].ticker == "NEW"


class TestValidateCommit:
    def test_auto_actions_pass(self):
        validator = AutopilotValidator()
        action = _make_action(weight_delta=0.005, confidence=0.90)
        ok, reason = validator.validate_commit(
            [action], AutopilotMode.HYBRID, pm_approved=False
        )
        assert ok

    def test_new_position_requires_approval(self):
        validator = AutopilotValidator()
        action = _make_action(is_new_position=True)
        ok, reason = validator.validate_commit(
            [action], AutopilotMode.HYBRID, pm_approved=False
        )
        assert not ok
        assert "approval" in reason.lower()

    def test_new_position_approved(self):
        validator = AutopilotValidator()
        action = _make_action(is_new_position=True)
        ok, reason = validator.validate_commit(
            [action], AutopilotMode.HYBRID, pm_approved=True
        )
        assert ok

    def test_full_manual_requires_approval(self):
        validator = AutopilotValidator()
        action = _make_action()
        ok, reason = validator.validate_commit(
            [action], AutopilotMode.FULL_MANUAL, pm_approved=False
        )
        assert not ok
