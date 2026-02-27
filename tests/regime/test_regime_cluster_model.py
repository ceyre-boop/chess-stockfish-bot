from copy import deepcopy

from engine.decision_frame import DecisionFrame
from engine.regime.regime_cluster_model import RegimeCluster, classify_regime


def _frame(**kwargs):
    return DecisionFrame(**kwargs)


# Structural regimes
def test_classify_quiet_accumulation_basic():
    frame = _frame(
        vol_regime="low", trend_regime="range", condition_vector={"regime": "A"}
    )
    res = classify_regime(frame)
    assert res.cluster == RegimeCluster.QUIET_ACCUMULATION


def test_classify_expansive_trend_basic():
    frame = _frame(vol_regime="elevated", trend_regime="up")
    res = classify_regime(frame)
    assert res.cluster == RegimeCluster.EXPANSIVE_TREND


def test_classify_choppy_manipulation_basic():
    frame = _frame(vol_regime="high", trend_regime="range")
    res = classify_regime(frame)
    assert res.cluster == RegimeCluster.CHOPPY_MANIPULATION


# News-aware regimes
def test_classify_news_pre_release_window():
    frame = _frame()
    frame.condition_vector = {"news_minutes_to_event": 8, "news_impact_score": 0.6}
    res = classify_regime(frame)
    assert res.cluster == RegimeCluster.NEWS_PRE_RELEASE_COMPRESSION


def test_classify_news_shock_explosion():
    frame = _frame()
    frame.condition_vector = {
        "news_minutes_to_event": 1,
        "news_impact_score": 0.9,
        "news_surprise_magnitude": 0.8,
        "trend_regime": "up",
    }
    res = classify_regime(frame)
    assert res.cluster == RegimeCluster.NEWS_SHOCK_EXPLOSION


def test_classify_news_post_digest_trend():
    frame = _frame(trend_regime="up")
    frame.condition_vector = {
        "news_minutes_to_event": -10,
        "news_impact_score": 0.7,
        "news_surprise_magnitude": 0.5,
    }
    res = classify_regime(frame)
    assert res.cluster == RegimeCluster.NEWS_POST_DIGESTION_TREND


# Additional regimes
def test_classify_volatility_breakout():
    frame = _frame(
        vol_regime="high",
        trend_regime="up",
        condition_vector={"impulse_strength": "strong"},
    )
    res = classify_regime(frame)
    assert res.cluster == RegimeCluster.VOLATILITY_BREAKOUT


def test_classify_liquidity_drain():
    frame = _frame(liquidity_frame={"state": "thin"})
    res = classify_regime(frame)
    assert res.cluster == RegimeCluster.LIQUIDITY_DRAIN


def test_classify_late_session_exhaustion():
    frame = _frame(session_profile="CLOSE")
    res = classify_regime(frame)
    assert res.cluster == RegimeCluster.LATE_SESSION_EXHAUSTION


# Determinism & stability
def test_regime_classification_deterministic_seed():
    frame = _frame(vol_regime="elevated", trend_regime="down")
    first = classify_regime(frame)
    second = classify_regime(deepcopy(frame))
    assert first.cluster == second.cluster
    assert first.confidence == second.confidence


def test_regime_classification_stability_small_perturbations():
    base = _frame()
    base.condition_vector = {
        "news_minutes_to_event": 8,
        "news_impact_score": 0.6,
        "trend_regime": "range",
    }
    first = classify_regime(base)

    perturbed = deepcopy(base)
    perturbed.condition_vector["news_impact_score"] = 0.62
    second = classify_regime(perturbed)

    assert first.cluster == second.cluster == RegimeCluster.NEWS_PRE_RELEASE_COMPRESSION


# Evidence & confidence
def test_regime_classification_evidence_fields_present():
    frame = _frame(vol_regime="quiet", trend_regime="range", session_profile="OPEN")
    res = classify_regime(frame)
    expected_keys = {
        "vol_regime",
        "trend_regime",
        "session",
        "regime",
        "liquidity_state",
        "news_minutes_to_event",
        "news_impact_score",
        "news_surprise_magnitude",
        "news_directional_bias",
        "reason",
    }
    assert 0.0 <= res.confidence <= 1.0
    assert res.evidence
    assert expected_keys.issubset(res.evidence.keys())
