from dataclasses import dataclass, field
from typing import List, Dict, Any
from copy import deepcopy
from engine.participants.participant_likelihood_model import ParticipantLikelihood, ParticipantType

@dataclass(frozen=True)
class ParticipantRiskLimits:
    max_size_multiplier: float
    max_concurrent_risk: float
    max_daily_risk: float
    no_trade: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

def get_participant_risk_limits(likelihoods: List[ParticipantLikelihood]) -> ParticipantRiskLimits:
    # Defaults (multiplicative, not absolute caps)
    max_size_multiplier = 1.0
    max_concurrent_risk = 1.0
    max_daily_risk = 1.0
    no_trade = False
    meta = {}
    probs = {l.type: l.probability for l in likelihoods}

    # SWEEP_BOT: reduce size, increase caution
    if probs.get(ParticipantType.SWEEP_BOT, 0.0) >= 0.15:
        max_size_multiplier *= 0.7
        max_concurrent_risk *= 0.9
        meta['sweep_bot_caution'] = True
    else:
        meta['sweep_bot_caution'] = False

    # LIQUIDITY_HUNTER: reduce size slightly
    if probs.get(ParticipantType.LIQUIDITY_HUNTER, 0.0) >= 0.15:
        max_size_multiplier *= 0.85
        meta['liquidity_hunter_caution'] = True
    else:
        meta['liquidity_hunter_caution'] = False

    # MARKET_MAKER: allow slightly wider stops (modeled as higher concurrent risk, but never >1.1)
    if probs.get(ParticipantType.MARKET_MAKER, 0.0) >= 0.15:
        max_concurrent_risk = min(max_concurrent_risk * 1.08, 1.1)
        meta['market_maker_wider_stops'] = True
    else:
        meta['market_maker_wider_stops'] = False

    # FUND: allow continuation but reduce leverage (modeled as lower size)
    if probs.get(ParticipantType.FUND, 0.0) >= 0.15:
        max_size_multiplier *= 0.9
        meta['fund_reduce_leverage'] = True
    else:
        meta['fund_reduce_leverage'] = False

    # NEWS_ALGO: no_trade during news
    if probs.get(ParticipantType.NEWS_ALGO, 0.0) >= 0.15:
        no_trade = True
        meta['news_algo_no_trade'] = True
    else:
        meta['news_algo_no_trade'] = False

    # RETAIL: small increase in noise tolerance, but never increase risk caps
    if probs.get(ParticipantType.RETAIL, 0.0) >= 0.15:
        meta['retail_noise_tolerance'] = True
    else:
        meta['retail_noise_tolerance'] = False

    return ParticipantRiskLimits(
        max_size_multiplier=max_size_multiplier,
        max_concurrent_risk=max_concurrent_risk,
        max_daily_risk=max_daily_risk,
        no_trade=no_trade,
        metadata=meta
    )

def enforce_participant_risk(frame, action, likelihoods, limits: ParticipantRiskLimits):
    # Assume frame has global/regime caps: frame['max_size'], frame['max_concurrent_risk'], frame['max_daily_risk']
    # action is a dict with at least: 'size', 'concurrent_risk', 'daily_risk', 'no_trade'
    # Do not mutate action
    adj = deepcopy(action)
    meta = {}
    # Enforce no_trade
    if limits.no_trade:
        adj['no_trade'] = True
        meta['no_trade'] = True
    else:
        adj['no_trade'] = action.get('no_trade', False)
        meta['no_trade'] = False
    # Enforce size
    capped_size = min(adj['size'], frame['max_size'] * limits.max_size_multiplier)
    adj['size'] = min(capped_size, frame['max_size'])
    meta['size_capped'] = adj['size'] < action['size']
    # Enforce concurrent risk
    capped_conc = min(adj['concurrent_risk'], frame['max_concurrent_risk'] * limits.max_concurrent_risk)
    adj['concurrent_risk'] = min(capped_conc, frame['max_concurrent_risk'])
    meta['concurrent_risk_capped'] = adj['concurrent_risk'] < action['concurrent_risk']
    # Enforce daily risk
    capped_daily = min(adj['daily_risk'], frame['max_daily_risk'] * limits.max_daily_risk)
    adj['daily_risk'] = min(capped_daily, frame['max_daily_risk'])
    meta['daily_risk_capped'] = adj['daily_risk'] < action['daily_risk']
    # Attach participant metadata
    adj['participant_risk_metadata'] = {**limits.metadata, **meta}
    # Preserve ordering
    ordered = {k: adj[k] for k in action.keys() if k in adj}
    for k in adj:
        if k not in ordered:
            ordered[k] = adj[k]
    return ordered
