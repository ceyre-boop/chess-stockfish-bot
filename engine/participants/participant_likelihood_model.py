from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List
from engine.participants.participant_taxonomy import ParticipantType
from engine.participants.participant_features import ParticipantFeatureVector

@dataclass(frozen=True)
class ParticipantLikelihood:
    type: ParticipantType
    probability: float
    evidence: Dict[str, Any]

def classify_participants(features: ParticipantFeatureVector) -> List[ParticipantLikelihood]:
    """
    Deterministically classify participant type likelihoods from feature vector.
    Returns a list of ParticipantLikelihood, sorted by ParticipantType name.
    """
    # Rule-based scoring (all weights deterministic)
    scores = {ptype: 1.0 for ptype in ParticipantType}  # base prior
    evidence = {ptype: {} for ptype in ParticipantType}

    # SWEEP_BOT: high sweep_intensity
    if features.sweep_intensity > 4.0:
        scores[ParticipantType.SWEEP_BOT] += 3.0
        evidence[ParticipantType.SWEEP_BOT]["high_sweep_intensity"] = True
    else:
        evidence[ParticipantType.SWEEP_BOT]["high_sweep_intensity"] = False

    # MARKET_MAKER: high absorption_ratio, low sweep_intensity
    if features.absorption_ratio > 1.5 and features.sweep_intensity < 2.0:
        scores[ParticipantType.MARKET_MAKER] += 2.5
        evidence[ParticipantType.MARKET_MAKER]["high_absorption_ratio"] = True
        evidence[ParticipantType.MARKET_MAKER]["low_sweep_intensity"] = True
    else:
        evidence[ParticipantType.MARKET_MAKER]["high_absorption_ratio"] = features.absorption_ratio > 1.5
        evidence[ParticipantType.MARKET_MAKER]["low_sweep_intensity"] = features.sweep_intensity < 2.0

    # ALGO: high orderflow_velocity, high volatility_reaction
    if features.orderflow_velocity > 4.0 and features.volatility_reaction > 1.5:
        scores[ParticipantType.ALGO] += 2.0
        evidence[ParticipantType.ALGO]["high_orderflow_velocity"] = True
        evidence[ParticipantType.ALGO]["high_volatility_reaction"] = True
    else:
        evidence[ParticipantType.ALGO]["high_orderflow_velocity"] = features.orderflow_velocity > 4.0
        evidence[ParticipantType.ALGO]["high_volatility_reaction"] = features.volatility_reaction > 1.5

    # LIQUIDITY_HUNTER: high liquidity_removal_rate
    if features.liquidity_removal_rate > 3.0:
        scores[ParticipantType.LIQUIDITY_HUNTER] += 2.0
        evidence[ParticipantType.LIQUIDITY_HUNTER]["high_liquidity_removal_rate"] = True
    else:
        evidence[ParticipantType.LIQUIDITY_HUNTER]["high_liquidity_removal_rate"] = False

    # RETAIL: open, low volatility
    if features.time_of_day_bias == "open" and features.volatility_reaction < 1.2:
        scores[ParticipantType.RETAIL] += 1.5
        evidence[ParticipantType.RETAIL]["open_and_low_volatility"] = True
    else:
        evidence[ParticipantType.RETAIL]["open_and_low_volatility"] = (
            features.time_of_day_bias == "open" and features.volatility_reaction < 1.2)

    # NEWS_ALGO: news window during, high volatility
    if features.news_window_behavior == "during" and features.volatility_reaction > 1.5:
        scores[ParticipantType.NEWS_ALGO] += 2.5
        evidence[ParticipantType.NEWS_ALGO]["news_during_and_high_volatility"] = True
    else:
        evidence[ParticipantType.NEWS_ALGO]["news_during_and_high_volatility"] = (
            features.news_window_behavior == "during" and features.volatility_reaction > 1.5)

    # FUND: mid, neutral vol (no size_profile available)
    if features.time_of_day_bias == "mid" and 0.8 < features.volatility_reaction < 1.3:
        scores[ParticipantType.FUND] += 1.5
        evidence[ParticipantType.FUND]["mid_neutral_vol"] = True
    else:
        evidence[ParticipantType.FUND]["mid_neutral_vol"] = (
            features.time_of_day_bias == "mid" and 0.8 < features.volatility_reaction < 1.3)

    # Normalize
    total = sum(scores.values())
    if total == 0:
        norm_scores = {ptype: 1.0 / len(scores) for ptype in scores}
    else:
        norm_scores = {ptype: v / total for ptype, v in scores.items()}

    # Build output, sorted by ParticipantType name
    likelihoods = [
        ParticipantLikelihood(type=ptype, probability=norm_scores[ptype], evidence=evidence[ptype])
        for ptype in sorted(ParticipantType, key=lambda x: x.name)
    ]
    return likelihoods
