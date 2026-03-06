"""Hybrid Autopilot Validator — classifies trade actions into AUTO/REVIEW buckets.

Critical governance rule: LLM/agents NEVER directly write portfolio state.
Only app-controlled commit functions may do it after validation.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from schemas.policy import AutopilotThresholds, Policy
from schemas.portfolio import BucketType, TradePlan, TradeAction
from quant.constraints import ConstraintsEngine


class AutopilotMode(str, Enum):
    FULL_MANUAL = "full_manual"
    HYBRID = "hybrid"
    FULL_AUTO = "full_auto"


class AutopilotValidator:
    def __init__(self, policy: Policy | None = None) -> None:
        self.policy = policy or Policy()
        self.thresholds = self.policy.autopilot
        self.constraints_engine = ConstraintsEngine(self.policy)

    def classify_action(self, action: TradeAction, plan: TradePlan) -> BucketType:
        """Classify a single trade action as AUTO or REVIEW.

        AUTO only if ALL safe conditions are met.
        REVIEW if ANY review trigger fires.
        """
        if action.is_new_position:
            return BucketType.REVIEW

        if action.is_full_exit:
            return BucketType.REVIEW

        if abs(action.weight_delta) > self.thresholds.max_weight_delta_auto:
            return BucketType.REVIEW

        if plan.total_turnover > self.thresholds.max_turnover_auto:
            return BucketType.REVIEW

        if action.confidence < self.thresholds.min_confidence_auto:
            return BucketType.REVIEW

        if any(
            flag in self.thresholds.high_risk_news_categories
            for flag in action.news_risk_flags
        ):
            return BucketType.REVIEW

        return BucketType.AUTO

    def classify_plan(self, plan: TradePlan, mode: AutopilotMode = AutopilotMode.HYBRID) -> TradePlan:
        """Classify all actions in a trade plan into AUTO and REVIEW buckets."""
        if mode == AutopilotMode.FULL_MANUAL:
            plan.auto_actions = []
            plan.review_actions = list(plan.actions)
            return plan

        if mode == AutopilotMode.FULL_AUTO:
            plan.auto_actions = list(plan.actions)
            plan.review_actions = []
            return plan

        auto_actions = []
        review_actions = []

        for action in plan.actions:
            bucket = self.classify_action(action, plan)
            if bucket == BucketType.AUTO:
                auto_actions.append(action)
            else:
                review_actions.append(action)

        # Final constraint check on auto-only actions
        if auto_actions:
            from schemas.portfolio import PortfolioState
            hypothetical = plan.portfolio_before or PortfolioState()
            alerts = self.constraints_engine.check_portfolio(hypothetical)
            if self.constraints_engine.has_critical_alerts(alerts):
                review_actions.extend(auto_actions)
                auto_actions = []

        plan.auto_actions = auto_actions
        plan.review_actions = review_actions
        return plan

    def validate_commit(self, actions: list[TradeAction], mode: AutopilotMode,
                        pm_approved: bool = False) -> tuple[bool, str]:
        """Final gate before committing trades to portfolio state.

        Returns (allowed, reason).
        """
        if mode == AutopilotMode.FULL_MANUAL and not pm_approved:
            return False, "Full-manual mode requires PM approval for all actions."

        for action in actions:
            if action.is_new_position and not pm_approved:
                return False, f"New position {action.ticker} requires PM approval."
            if action.is_full_exit and not pm_approved:
                return False, f"Full exit of {action.ticker} requires PM approval."
            if abs(action.weight_delta) > 0.02 and not pm_approved:
                return False, (
                    f"{action.ticker} weight delta {action.weight_delta:.1%} > 2% "
                    f"requires approval."
                )
            if action.confidence < 0.70 and not pm_approved:
                return False, (
                    f"{action.ticker} confidence {action.confidence:.0%} < 70% "
                    f"requires approval."
                )

        return True, "All validations passed."
