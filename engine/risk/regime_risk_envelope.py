from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from engine.decision_actions import ActionType, DecisionAction
from engine.decision_frame import DecisionFrame
from engine.pattern_templates import PatternFamily
from engine.regime.regime_cluster_model import RegimeCluster

# Global caps (do not exceed)
_GLOBAL_MAX_PER_TRADE_R = 1.0
_GLOBAL_MAX_CONCURRENT_R = 3.0
_GLOBAL_MAX_DAILY_R = 5.0


@dataclass(frozen=True)
class RegimeRiskLimits:
    regime: RegimeCluster
    max_per_trade_R: float
    max_concurrent_R: float
    max_daily_R: float
    allowed_action_types: List[str]
    allowed_template_families: List[PatternFamily]
    news_rules: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class RegimeRiskDecision:
    allowed: bool
    reason: str
    adjusted_size: float | None
    metadata: Dict[str, Any]


def _clamp(val: float, cap: float) -> float:
    return float(min(max(val, 0.0), cap))


def get_regime_risk_limits(cluster: RegimeCluster) -> RegimeRiskLimits:
    base = RegimeRiskLimits(
        regime=cluster,
        max_per_trade_R=_GLOBAL_MAX_PER_TRADE_R,
        max_concurrent_R=_GLOBAL_MAX_CONCURRENT_R,
        max_daily_R=_GLOBAL_MAX_DAILY_R,
        allowed_action_types=[a.value for a in ActionType],
        allowed_template_families=list(PatternFamily),
        news_rules={},
        metadata={},
    )

    overrides: Dict[RegimeCluster, Dict[str, Any]] = {
        RegimeCluster.NEWS_SHOCK_EXPLOSION: {
            "max_per_trade_R": 0.0,
            "max_concurrent_R": 0.0,
            "max_daily_R": 0.0,
            "allowed_action_types": [ActionType.NO_TRADE.value],
            "allowed_template_families": [],
            "news_rules": {"block_fresh_entry": True},
        },
        RegimeCluster.NEWS_PRE_RELEASE_COMPRESSION: {
            "max_per_trade_R": 0.3,
            "max_concurrent_R": 1.0,
            "max_daily_R": 1.5,
            "allowed_action_types": [
                ActionType.OPEN_LONG.value,
                ActionType.OPEN_SHORT.value,
            ],
            "allowed_template_families": [
                PatternFamily.LIQUIDITY,
                PatternFamily.MEAN_REVERSION,
            ],
            "news_rules": {"restrict_continuation": True},
        },
        RegimeCluster.NEWS_POST_DIGESTION_TREND: {
            "max_per_trade_R": 0.6,
            "max_concurrent_R": 2.0,
            "max_daily_R": 3.0,
            "allowed_action_types": [
                ActionType.OPEN_LONG.value,
                ActionType.OPEN_SHORT.value,
            ],
            "allowed_template_families": [
                PatternFamily.LIQUIDITY,
                PatternFamily.CONTINUATION,
            ],
            "news_rules": {"boost_liquidity": True},
        },
        RegimeCluster.EXPANSIVE_TREND: {
            "max_per_trade_R": 0.9,
            "allowed_template_families": [
                PatternFamily.CONTINUATION,
                PatternFamily.LIQUIDITY,
                PatternFamily.HYBRID,
            ],
        },
        RegimeCluster.CHOPPY_MANIPULATION: {
            "max_per_trade_R": 0.6,
            "max_concurrent_R": 2.0,
            "max_daily_R": 3.0,
            "allowed_template_families": [
                PatternFamily.MEAN_REVERSION,
                PatternFamily.LIQUIDITY,
            ],
        },
        RegimeCluster.VOLATILITY_BREAKOUT: {
            "max_per_trade_R": 0.7,
            "max_concurrent_R": 2.5,
            "max_daily_R": 4.0,
            "allowed_template_families": [
                PatternFamily.CONTINUATION,
                PatternFamily.IMBALANCE,
            ],
        },
        RegimeCluster.LIQUIDITY_DRAIN: {
            "max_per_trade_R": 0.5,
            "max_concurrent_R": 1.5,
            "max_daily_R": 2.0,
            "allowed_template_families": [
                PatternFamily.LIQUIDITY,
                PatternFamily.MEAN_REVERSION,
            ],
        },
        RegimeCluster.QUIET_ACCUMULATION: {
            "max_per_trade_R": 1.0,
        },
    }

    ov = overrides.get(cluster, {})
    limits = RegimeRiskLimits(
        regime=cluster,
        max_per_trade_R=_clamp(
            float(ov.get("max_per_trade_R", base.max_per_trade_R)),
            _GLOBAL_MAX_PER_TRADE_R,
        ),
        max_concurrent_R=_clamp(
            float(ov.get("max_concurrent_R", base.max_concurrent_R)),
            _GLOBAL_MAX_CONCURRENT_R,
        ),
        max_daily_R=_clamp(
            float(ov.get("max_daily_R", base.max_daily_R)), _GLOBAL_MAX_DAILY_R
        ),
        allowed_action_types=ov.get("allowed_action_types", base.allowed_action_types),
        allowed_template_families=ov.get(
            "allowed_template_families", base.allowed_template_families
        ),
        news_rules=ov.get("news_rules", base.news_rules),
        metadata={"source": "regime_risk_limits"},
    )
    return limits


def enforce_regime_risk(
    frame: DecisionFrame,
    action: DecisionAction,
    cluster: RegimeCluster,
    limits: RegimeRiskLimits,
    *,
    current_concurrent_R: float = 0.0,
    current_daily_R: float = 0.0,
) -> RegimeRiskDecision:
    applied_rules: List[str] = []

    if cluster == RegimeCluster.NEWS_SHOCK_EXPLOSION and limits.news_rules.get(
        "block_fresh_entry"
    ):
        return RegimeRiskDecision(
            allowed=False,
            reason="blocked_by_news_shock",
            adjusted_size=0.0,
            metadata={"applied_rules": ["news_shock_block"]},
        )

    action_type_value = (
        action.action_type.value
        if hasattr(action, "action_type")
        else str(action.action_type)
    )
    if (
        limits.allowed_action_types
        and action_type_value not in limits.allowed_action_types
    ):
        return RegimeRiskDecision(
            allowed=False,
            reason="action_type_not_allowed",
            adjusted_size=0.0,
            metadata={"applied_rules": ["action_type_filter"]},
        )

    tmpl_family = getattr(action, "template_family", None)
    if tmpl_family and limits.allowed_template_families:
        allowed_values = {
            f.value if isinstance(f, PatternFamily) else str(f)
            for f in limits.allowed_template_families
        }
        if tmpl_family not in allowed_values:
            return RegimeRiskDecision(
                allowed=False,
                reason="template_family_not_allowed",
                adjusted_size=0.0,
                metadata={"applied_rules": ["template_family_filter"]},
            )

    requested_r = getattr(frame, "risk_per_trade", None)
    adjusted = None
    if isinstance(requested_r, (int, float)):
        adjusted = _clamp(float(requested_r), limits.max_per_trade_R)
        if adjusted < requested_r:
            applied_rules.append("size_capped_regime")

    if current_concurrent_R > limits.max_concurrent_R:
        return RegimeRiskDecision(
            allowed=False,
            reason="concurrent_risk_exceeds_regime",
            adjusted_size=adjusted,
            metadata={"applied_rules": applied_rules},
        )

    if current_daily_R > limits.max_daily_R:
        return RegimeRiskDecision(
            allowed=False,
            reason="daily_risk_exceeds_regime",
            adjusted_size=adjusted,
            metadata={"applied_rules": applied_rules},
        )

    return RegimeRiskDecision(
        allowed=True,
        reason="allowed",
        adjusted_size=adjusted,
        metadata={"applied_rules": applied_rules},
    )
