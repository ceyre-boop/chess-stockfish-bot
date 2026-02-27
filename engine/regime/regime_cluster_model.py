from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from engine.decision_frame import DecisionFrame


class RegimeCluster(str, Enum):
    QUIET_ACCUMULATION = "quiet_accumulation"
    EXPANSIVE_TREND = "expansive_trend"
    CHOPPY_MANIPULATION = "choppy_manipulation"
    NEWS_PRE_RELEASE_COMPRESSION = "news_pre_release_compression"
    NEWS_SHOCK_EXPLOSION = "news_shock_explosion"
    NEWS_POST_DIGESTION_TREND = "news_post_digestive_trend"
    LATE_SESSION_EXHAUSTION = "late_session_exhaustion"
    VOLATILITY_BREAKOUT = "volatility_breakout"
    LIQUIDITY_DRAIN = "liquidity_drain"


@dataclass(frozen=True)
class RegimeClusterResult:
    cluster: RegimeCluster
    confidence: float
    evidence: Dict[str, Any]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _get(frame: DecisionFrame, key: str) -> Optional[Any]:
    cv = frame.condition_vector or {}
    if isinstance(cv, dict) and key in cv:
        return cv.get(key)
    return getattr(frame, key, None)


def classify_regime(frame: DecisionFrame) -> RegimeClusterResult:
    """Deterministically classify a frame into a RegimeCluster."""

    vol = _get(frame, "vol_regime") or _get(frame, "vol") or "unknown"
    trend = _get(frame, "trend_regime") or _get(frame, "trend") or "unknown"
    session = frame.session_profile or _get(frame, "session") or None
    regime = _get(frame, "regime") or None
    liquidity_state = None
    if isinstance(frame.liquidity_frame, dict):
        liquidity_state = frame.liquidity_frame.get(
            "state"
        ) or frame.liquidity_frame.get("liquidity")

    news_minutes_to_event = getattr(frame, "news_minutes_to_event", None) or _get(
        frame, "news_minutes_to_event"
    )
    news_impact = getattr(frame, "news_impact_score", None) or _get(
        frame, "news_impact_score"
    )
    news_bias = getattr(frame, "news_directional_bias", None) or _get(
        frame, "news_directional_bias"
    )
    news_surprise = getattr(frame, "news_surprise_magnitude", None) or _get(
        frame, "news_surprise_magnitude"
    )

    evidence: Dict[str, Any] = {
        "vol_regime": vol,
        "trend_regime": trend,
        "session": session,
        "regime": regime,
        "liquidity_state": liquidity_state,
        "news_minutes_to_event": news_minutes_to_event,
        "news_impact_score": news_impact,
        "news_surprise_magnitude": news_surprise,
        "news_directional_bias": news_bias,
    }

    def result(
        cluster: RegimeCluster, confidence: float, reason: str
    ) -> RegimeClusterResult:
        evidence["reason"] = reason
        return RegimeClusterResult(
            cluster=cluster, confidence=_clamp(confidence), evidence=evidence
        )

    # News-aware branches (priority ordered)
    if news_minutes_to_event is not None:
        if (
            abs(news_minutes_to_event) <= 5
            and (news_impact or 0) >= 0.7
            and (news_surprise or 0) >= 0.6
        ):
            return result(RegimeCluster.NEWS_SHOCK_EXPLOSION, 0.9, "news_shock")

        if 0 <= news_minutes_to_event <= 10:
            return result(
                RegimeCluster.NEWS_PRE_RELEASE_COMPRESSION, 0.82, "news_pre_release"
            )

        if -20 <= news_minutes_to_event <= -5 and trend in {"up", "down", "trend"}:
            return result(
                RegimeCluster.NEWS_POST_DIGESTION_TREND, 0.78, "news_post_digest"
            )

    # Structural regimes
    if vol in {"elevated", "high"} and trend in {"up", "down"}:
        impulse_strength = _get(frame, "impulse_strength") or _get(
            frame, "displacement"
        )
        if impulse_strength in {"strong", "up", "down"} or (news_surprise or 0) > 0.4:
            return result(RegimeCluster.VOLATILITY_BREAKOUT, 0.7, "volatility_breakout")

    if liquidity_state in {"thin", "illiquid", "dry"}:
        return result(RegimeCluster.LIQUIDITY_DRAIN, 0.66, "liquidity_drain")

    if vol in {"elevated", "high"} and trend in {"range", "chop", "sideways"}:
        return result(RegimeCluster.CHOPPY_MANIPULATION, 0.6, "choppy_structure")

    if vol in {"normal", "elevated", "high", "expansive"} and trend in {"up", "down"}:
        return result(RegimeCluster.EXPANSIVE_TREND, 0.64, "trend_structure")

    if vol in {"low", "quiet"} or regime == "A":
        return result(RegimeCluster.QUIET_ACCUMULATION, 0.58, "quiet_structure")

    if session and ("CLOSE" in session or session.startswith("3") or "LATE" in session):
        return result(RegimeCluster.LATE_SESSION_EXHAUSTION, 0.52, "late_session")

    return result(RegimeCluster.QUIET_ACCUMULATION, 0.5, "fallback_quiet")
