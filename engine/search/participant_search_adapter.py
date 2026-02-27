from dataclasses import dataclass
from typing import List, Dict, Any
from engine.participants.participant_likelihood_model import ParticipantLikelihood
from engine.participants.participant_taxonomy import ParticipantType

@dataclass(frozen=True)
class ParticipantScoringWeights:
    ev_weight: float
    mcr_weight: float
    variance_weight: float
    tail_risk_weight: float
    rollout_horizon: int
    path_count: int
    metadata: Dict[str, Any]

def get_participant_scoring_weights(likelihoods: List[ParticipantLikelihood]) -> ParticipantScoringWeights:
    # Base weights
    ev_weight = 1.0
    mcr_weight = 1.0
    variance_weight = 1.0
    tail_risk_weight = 1.0
    rollout_horizon = 10
    path_count = 16
    meta = {}

    # Map for quick lookup
    probs = {l.type: l.probability for l in likelihoods}

    # SWEEP_BOT: increase tail risk
    if probs.get(ParticipantType.SWEEP_BOT, 0.0) >= 0.15:
        tail_risk_weight += 0.5
        meta['sweep_bot_tail_risk'] = True
    else:
        meta['sweep_bot_tail_risk'] = False

    # LIQUIDITY_HUNTER: increase variance
    if probs.get(ParticipantType.LIQUIDITY_HUNTER, 0.0) >= 0.15:
        variance_weight += 0.5
        meta['liquidity_hunter_variance'] = True
    else:
        meta['liquidity_hunter_variance'] = False

    # MARKET_MAKER: increase mean-reversion (lower EV weight)
    if probs.get(ParticipantType.MARKET_MAKER, 0.0) >= 0.15:
        ev_weight -= 0.2
        mcr_weight += 0.2
        meta['market_maker_mean_reversion'] = True
    else:
        meta['market_maker_mean_reversion'] = False

    # FUND: increase trend-continuation (increase EV weight)
    if probs.get(ParticipantType.FUND, 0.0) >= 0.15:
        ev_weight += 0.3
        meta['fund_trend_continuation'] = True
    else:
        meta['fund_trend_continuation'] = False

    # NEWS_ALGO: shorten horizon, increase variance
    if probs.get(ParticipantType.NEWS_ALGO, 0.0) >= 0.15:
        rollout_horizon = max(3, rollout_horizon - 4)
        variance_weight += 0.5
        meta['news_algo_short_horizon'] = True
    else:
        meta['news_algo_short_horizon'] = False

    # RETAIL: increase path count
    if probs.get(ParticipantType.RETAIL, 0.0) >= 0.15:
        path_count += 4
        meta['retail_path_count'] = True
    else:
        meta['retail_path_count'] = False

    # Clamp weights to reasonable ranges
    ev_weight = max(0.1, min(ev_weight, 2.0))
    mcr_weight = max(0.1, min(mcr_weight, 2.0))
    variance_weight = max(0.1, min(variance_weight, 3.0))
    tail_risk_weight = max(0.1, min(tail_risk_weight, 3.0))
    rollout_horizon = max(1, min(rollout_horizon, 20))
    path_count = max(4, min(path_count, 64))

    return ParticipantScoringWeights(
        ev_weight=ev_weight,
        mcr_weight=mcr_weight,
        variance_weight=variance_weight,
        tail_risk_weight=tail_risk_weight,
        rollout_horizon=rollout_horizon,
        path_count=path_count,
        metadata=meta,
    )
