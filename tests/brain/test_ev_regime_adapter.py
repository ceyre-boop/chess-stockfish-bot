from copy import deepcopy

from engine.brain.ev_regime_adapter import build_ev_features_with_regime
from engine.regime.regime_cluster_model import RegimeCluster, RegimeClusterResult


def _regime_result(cluster: RegimeCluster) -> RegimeClusterResult:
    return RegimeClusterResult(cluster=cluster, confidence=0.9, evidence={})


def test_ev_features_include_regime_fields():
    base = {"base_feature": 1.0}
    regime_result = _regime_result(RegimeCluster.EXPANSIVE_TREND)

    extended = build_ev_features_with_regime(base, regime_result, {})

    one_hot = extended["regime_one_hot"]
    expected_keys = {c.value for c in RegimeCluster}
    assert set(one_hot.keys()) == expected_keys
    assert one_hot[RegimeCluster.EXPANSIVE_TREND.value] == 1
    assert sum(one_hot.values()) == 1

    # deterministic mapping
    extended_again = build_ev_features_with_regime(base, regime_result, {})
    assert extended_again["regime_one_hot"] == one_hot


def test_ev_features_include_news_fields():
    base = {"foo": 2.0}
    regime_result = _regime_result(RegimeCluster.CHOPPY_MANIPULATION)
    news = {
        "news_minutes_to_event": 15,
        "news_impact_score": 0.8,
        "news_directional_bias": -0.25,
        "news_surprise_magnitude": 0.6,
    }

    extended = build_ev_features_with_regime(base, regime_result, news)

    assert extended["news_proximity_minutes"] == 15.0
    assert extended["news_impact_score"] == 0.8
    assert extended["news_directional_bias"] == -0.25
    assert extended["news_surprise_magnitude"] == 0.6

    # stability on repeated calls
    extended_again = build_ev_features_with_regime(base, regime_result, news)
    assert (
        extended_again["news_proximity_minutes"] == extended["news_proximity_minutes"]
    )
    assert extended_again["news_impact_score"] == extended["news_impact_score"]


def test_ev_features_preserve_base_features():
    base = {"a": 1.0, "nested": {"keep": True}}
    snapshot = deepcopy(base)
    regime_result = _regime_result(RegimeCluster.VOLATILITY_BREAKOUT)

    extended = build_ev_features_with_regime(base, regime_result, {})

    assert base == snapshot
    assert "regime_one_hot" not in base
    assert extended["a"] == 1.0
    assert extended["nested"] == {"keep": True}


def test_ev_feature_extension_deterministic():
    base = {"feature": 3.14}
    regime_result = _regime_result(RegimeCluster.LIQUIDITY_DRAIN)
    news = {
        "news_minutes_to_event": 0,
        "news_impact_score": 0.0,
        "news_directional_bias": 0.0,
        "news_surprise_magnitude": 0.0,
    }

    first = build_ev_features_with_regime(base, regime_result, news)
    second = build_ev_features_with_regime(base, regime_result, news)

    assert first == second
    assert set(first["regime_one_hot"].keys()) == {c.value for c in RegimeCluster}
