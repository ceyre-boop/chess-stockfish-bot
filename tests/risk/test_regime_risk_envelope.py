import pytest

from engine.decision_actions import ActionType, DecisionAction
from engine.decision_frame import DecisionFrame
from engine.pattern_templates import PatternFamily
from engine.regime.regime_cluster_model import RegimeCluster
from engine.risk.regime_risk_envelope import enforce_regime_risk, get_regime_risk_limits


def _action(action_type: ActionType, family: PatternFamily) -> DecisionAction:
    return DecisionAction(
        action_type=action_type,
        template_family=family.value,
    )


def test_regime_risk_limits_loaded_correctly():
    shock = get_regime_risk_limits(RegimeCluster.NEWS_SHOCK_EXPLOSION)
    pre = get_regime_risk_limits(RegimeCluster.NEWS_PRE_RELEASE_COMPRESSION)
    post = get_regime_risk_limits(RegimeCluster.NEWS_POST_DIGESTION_TREND)
    choppy = get_regime_risk_limits(RegimeCluster.CHOPPY_MANIPULATION)

    assert shock.max_per_trade_R == 0.0
    assert pre.max_per_trade_R < post.max_per_trade_R < 1.0
    assert choppy.max_concurrent_R <= 2.0

    for limits in [shock, pre, post, choppy]:
        assert limits.max_per_trade_R <= 1.0
        assert limits.max_concurrent_R <= 3.0
        assert limits.max_daily_R <= 5.0


def test_regime_risk_limits_enforced_correctly():
    limits = get_regime_risk_limits(RegimeCluster.CHOPPY_MANIPULATION)

    frame = DecisionFrame(risk_per_trade=0.8)
    action = _action(ActionType.OPEN_LONG, PatternFamily.MEAN_REVERSION)

    blocked_concurrent = enforce_regime_risk(
        frame,
        action,
        RegimeCluster.CHOPPY_MANIPULATION,
        limits,
        current_concurrent_R=2.5,
    )
    assert not blocked_concurrent.allowed
    assert blocked_concurrent.reason == "concurrent_risk_exceeds_regime"

    blocked_daily = enforce_regime_risk(
        frame,
        action,
        RegimeCluster.CHOPPY_MANIPULATION,
        limits,
        current_daily_R=3.5,
    )
    assert not blocked_daily.allowed
    assert blocked_daily.reason == "daily_risk_exceeds_regime"

    allowed = enforce_regime_risk(
        frame,
        action,
        RegimeCluster.CHOPPY_MANIPULATION,
        limits,
        current_concurrent_R=1.0,
        current_daily_R=1.5,
    )
    assert allowed.allowed
    assert allowed.adjusted_size == pytest.approx(0.6)
    assert "size_capped_regime" in allowed.metadata.get("applied_rules", [])


def test_news_shock_forces_no_trade():
    limits = get_regime_risk_limits(RegimeCluster.NEWS_SHOCK_EXPLOSION)
    frame = DecisionFrame(risk_per_trade=0.5)
    action = _action(ActionType.OPEN_LONG, PatternFamily.LIQUIDITY)

    decision = enforce_regime_risk(
        frame,
        action,
        RegimeCluster.NEWS_SHOCK_EXPLOSION,
        limits,
    )

    assert not decision.allowed
    assert decision.adjusted_size == 0.0
    assert decision.reason == "blocked_by_news_shock"


def test_pre_release_reduces_size():
    limits = get_regime_risk_limits(RegimeCluster.NEWS_PRE_RELEASE_COMPRESSION)
    frame = DecisionFrame(risk_per_trade=0.9)

    disallowed = enforce_regime_risk(
        frame,
        _action(ActionType.OPEN_LONG, PatternFamily.CONTINUATION),
        RegimeCluster.NEWS_PRE_RELEASE_COMPRESSION,
        limits,
    )
    assert not disallowed.allowed
    assert disallowed.reason == "template_family_not_allowed"

    allowed = enforce_regime_risk(
        frame,
        _action(ActionType.OPEN_SHORT, PatternFamily.LIQUIDITY),
        RegimeCluster.NEWS_PRE_RELEASE_COMPRESSION,
        limits,
    )
    assert allowed.allowed
    assert allowed.adjusted_size == pytest.approx(0.3)
    assert "size_capped_regime" in allowed.metadata.get("applied_rules", [])


def test_post_digest_cautious_continuation():
    limits = get_regime_risk_limits(RegimeCluster.NEWS_POST_DIGESTION_TREND)
    frame = DecisionFrame(risk_per_trade=0.8)
    action = _action(ActionType.OPEN_SHORT, PatternFamily.CONTINUATION)

    decision = enforce_regime_risk(
        frame,
        action,
        RegimeCluster.NEWS_POST_DIGESTION_TREND,
        limits,
    )

    assert decision.allowed
    assert decision.adjusted_size == pytest.approx(0.6)
    assert decision.metadata.get("applied_rules") == ["size_capped_regime"]


def test_regime_risk_never_exceeds_global_caps():
    for cluster in RegimeCluster:
        limits = get_regime_risk_limits(cluster)
        assert limits.max_per_trade_R <= 1.0
        assert limits.max_concurrent_R <= 3.0
        assert limits.max_daily_R <= 5.0


def test_regime_risk_enforcement_deterministic():
    limits = get_regime_risk_limits(RegimeCluster.LIQUIDITY_DRAIN)
    frame = DecisionFrame(risk_per_trade=0.4)
    action = _action(ActionType.OPEN_LONG, PatternFamily.LIQUIDITY)

    first = enforce_regime_risk(
        frame,
        action,
        RegimeCluster.LIQUIDITY_DRAIN,
        limits,
        current_concurrent_R=0.5,
        current_daily_R=0.5,
    )
    second = enforce_regime_risk(
        frame,
        action,
        RegimeCluster.LIQUIDITY_DRAIN,
        limits,
        current_concurrent_R=0.5,
        current_daily_R=0.5,
    )

    assert first == second
    assert first.allowed
    assert first.metadata == second.metadata
