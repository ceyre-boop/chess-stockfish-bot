from typing import Any, Dict, List, Tuple
from copy import deepcopy
from engine.participants.participant_likelihood_model import ParticipantLikelihood, ParticipantType

def adjust_template_policy_by_participants(template_policy: Any, likelihoods: List[ParticipantLikelihood]) -> Tuple[Any, Dict[str, Any]]:
    """
    Returns a new template policy object with participant-aware adjustments and metadata.
    Does not mutate the input policy.
    """
    policy = deepcopy(template_policy)
    meta = {}
    probs = {l.type: l.probability for l in likelihoods}

    # MARKET_MAKER: mean-reversion up, breakout down
    if probs.get(ParticipantType.MARKET_MAKER, 0.0) >= 0.15:
        if 'mean_reversion_weight' in policy:
            policy['mean_reversion_weight'] += 0.2
        meta['market_maker_mean_reversion'] = True
        if 'breakout_weight' in policy:
            policy['breakout_weight'] = max(0, policy['breakout_weight'] - 0.1)
        meta['market_maker_breakout_down'] = True
    else:
        meta['market_maker_mean_reversion'] = False
        meta['market_maker_breakout_down'] = False

    # SWEEP_BOT: sweep-reversal up, thin-liquidity down
    if probs.get(ParticipantType.SWEEP_BOT, 0.0) >= 0.15:
        if 'sweep_reversal_weight' in policy:
            policy['sweep_reversal_weight'] += 0.2
        meta['sweep_bot_sweep_reversal'] = True
        if 'thin_liquidity_weight' in policy:
            policy['thin_liquidity_weight'] = max(0, policy['thin_liquidity_weight'] - 0.1)
        meta['sweep_bot_thin_liquidity_down'] = True
    else:
        meta['sweep_bot_sweep_reversal'] = False
        meta['sweep_bot_thin_liquidity_down'] = False

    # FUND: trend-continuation up, counter-trend down
    if probs.get(ParticipantType.FUND, 0.0) >= 0.15:
        if 'trend_continuation_weight' in policy:
            policy['trend_continuation_weight'] += 0.2
        meta['fund_trend_continuation'] = True
        if 'counter_trend_weight' in policy:
            policy['counter_trend_weight'] = max(0, policy['counter_trend_weight'] - 0.1)
        meta['fund_counter_trend_down'] = True
    else:
        meta['fund_trend_continuation'] = False
        meta['fund_counter_trend_down'] = False

    # NEWS_ALGO: discourage continuation during news
    if probs.get(ParticipantType.NEWS_ALGO, 0.0) >= 0.15:
        if 'continuation_during_news' in policy:
            policy['continuation_during_news'] = False
        meta['news_algo_discourage_continuation'] = True
    else:
        meta['news_algo_discourage_continuation'] = False

    # LIQUIDITY_HUNTER: breakout caution up, reversal up
    if probs.get(ParticipantType.LIQUIDITY_HUNTER, 0.0) >= 0.15:
        if 'breakout_caution_weight' in policy:
            policy['breakout_caution_weight'] += 0.1
        meta['liquidity_hunter_breakout_caution'] = True
        if 'reversal_weight' in policy:
            policy['reversal_weight'] += 0.05
        meta['liquidity_hunter_reversal_up'] = True
    else:
        meta['liquidity_hunter_breakout_caution'] = False
        meta['liquidity_hunter_reversal_up'] = False

    # RETAIL: path_count or noise_tolerance up
    if probs.get(ParticipantType.RETAIL, 0.0) >= 0.15:
        if 'path_count' in policy:
            policy['path_count'] += 2
        if 'noise_tolerance' in policy:
            policy['noise_tolerance'] += 0.05
        meta['retail_noise_tolerance'] = True
    else:
        meta['retail_noise_tolerance'] = False

    # Preserve key ordering if dict
    if isinstance(template_policy, dict):
        ordered = {k: policy[k] for k in template_policy.keys() if k in policy}
        for k in policy:
            if k not in ordered:
                ordered[k] = policy[k]
        policy = ordered
    return policy, meta

def adjust_entry_policy_by_participants(entry_policy: Any, likelihoods: List[ParticipantLikelihood]) -> Tuple[Any, Dict[str, Any]]:
    """
    Returns a new entry policy object with participant-aware adjustments and metadata.
    Does not mutate the input policy.
    """
    policy = deepcopy(entry_policy)
    meta = {}
    probs = {l.type: l.probability for l in likelihoods}

    # MARKET_MAKER: mean-reversion up, breakout down
    if probs.get(ParticipantType.MARKET_MAKER, 0.0) >= 0.15:
        if 'mean_reversion_entry' in policy:
            policy['mean_reversion_entry'] += 0.2
        meta['market_maker_mean_reversion_entry'] = True
        if 'breakout_entry' in policy:
            policy['breakout_entry'] = max(0, policy['breakout_entry'] - 0.1)
        meta['market_maker_breakout_entry_down'] = True
    else:
        meta['market_maker_mean_reversion_entry'] = False
        meta['market_maker_breakout_entry_down'] = False

    # SWEEP_BOT: sweep-reversal up, thin-liquidity down
    if probs.get(ParticipantType.SWEEP_BOT, 0.0) >= 0.15:
        if 'sweep_reversal_entry' in policy:
            policy['sweep_reversal_entry'] += 0.2
        meta['sweep_bot_sweep_reversal_entry'] = True
        if 'thin_liquidity_entry' in policy:
            policy['thin_liquidity_entry'] = max(0, policy['thin_liquidity_entry'] - 0.1)
        meta['sweep_bot_thin_liquidity_entry_down'] = True
    else:
        meta['sweep_bot_sweep_reversal_entry'] = False
        meta['sweep_bot_thin_liquidity_entry_down'] = False

    # FUND: trend-continuation up, counter-trend down
    if probs.get(ParticipantType.FUND, 0.0) >= 0.15:
        if 'trend_continuation_entry' in policy:
            policy['trend_continuation_entry'] += 0.2
        meta['fund_trend_continuation_entry'] = True
        if 'counter_trend_entry' in policy:
            policy['counter_trend_entry'] = max(0, policy['counter_trend_entry'] - 0.1)
        meta['fund_counter_trend_entry_down'] = True
    else:
        meta['fund_trend_continuation_entry'] = False
        meta['fund_counter_trend_entry_down'] = False

    # NEWS_ALGO: discourage continuation during news
    if probs.get(ParticipantType.NEWS_ALGO, 0.0) >= 0.15:
        if 'continuation_entry_during_news' in policy:
            policy['continuation_entry_during_news'] = False
        meta['news_algo_discourage_continuation_entry'] = True
    else:
        meta['news_algo_discourage_continuation_entry'] = False

    # LIQUIDITY_HUNTER: breakout caution up, reversal up
    if probs.get(ParticipantType.LIQUIDITY_HUNTER, 0.0) >= 0.15:
        if 'breakout_caution_entry' in policy:
            policy['breakout_caution_entry'] += 0.1
        meta['liquidity_hunter_breakout_caution_entry'] = True
        if 'reversal_entry' in policy:
            policy['reversal_entry'] += 0.05
        meta['liquidity_hunter_reversal_entry_up'] = True
    else:
        meta['liquidity_hunter_breakout_caution_entry'] = False
        meta['liquidity_hunter_reversal_entry_up'] = False

    # RETAIL: path_count or noise_tolerance up
    if probs.get(ParticipantType.RETAIL, 0.0) >= 0.15:
        if 'path_count' in policy:
            policy['path_count'] += 2
        if 'noise_tolerance' in policy:
            policy['noise_tolerance'] += 0.05
        meta['retail_noise_tolerance_entry'] = True
    else:
        meta['retail_noise_tolerance_entry'] = False

    # Preserve key ordering if dict
    if isinstance(entry_policy, dict):
        ordered = {k: policy[k] for k in entry_policy.keys() if k in policy}
        for k in policy:
            if k not in ordered:
                ordered[k] = policy[k]
        policy = ordered
    return policy, meta
