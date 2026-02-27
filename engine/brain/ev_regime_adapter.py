from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from engine.regime.regime_cluster_model import RegimeCluster, RegimeClusterResult


@dataclass(frozen=True)
class RegimeEVFeatures:
    regime_one_hot: Dict[str, int]
    news_proximity_minutes: float
    news_impact_score: float
    news_directional_bias: float
    news_surprise_magnitude: float
    metadata: Dict[str, Any]


def _one_hot(cluster: RegimeCluster) -> Dict[str, int]:
    return {c.value: (1 if c == cluster else 0) for c in RegimeCluster}


def _get_news_value(context: Dict[str, Any], key: str) -> float:
    try:
        val = context.get(key, 0.0)
        return float(val) if val is not None else 0.0
    except Exception:
        return 0.0


def build_ev_features_with_regime(
    base_features: Dict[str, Any],
    regime_result: RegimeClusterResult,
    news_context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Extend base EV features with regime/news fields deterministically.
    """

    extended = dict(base_features or {})

    regime_features = RegimeEVFeatures(
        regime_one_hot=_one_hot(regime_result.cluster),
        news_proximity_minutes=_get_news_value(
            news_context or {}, "news_minutes_to_event"
        ),
        news_impact_score=_get_news_value(news_context or {}, "news_impact_score"),
        news_directional_bias=_get_news_value(
            news_context or {}, "news_directional_bias"
        ),
        news_surprise_magnitude=_get_news_value(
            news_context or {}, "news_surprise_magnitude"
        ),
        metadata={"source": "regime_adapter"},
    )

    extended["regime_one_hot"] = regime_features.regime_one_hot
    extended["news_proximity_minutes"] = regime_features.news_proximity_minutes
    extended["news_impact_score"] = regime_features.news_impact_score
    extended["news_directional_bias"] = regime_features.news_directional_bias
    extended["news_surprise_magnitude"] = regime_features.news_surprise_magnitude

    return extended
