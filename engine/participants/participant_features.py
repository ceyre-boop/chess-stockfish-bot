from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

@dataclass(frozen=True)
class ParticipantFeatureVector:
    orderflow_velocity: float
    sweep_intensity: float
    absorption_ratio: float
    spread_pressure: float
    liquidity_removal_rate: float
    volatility_reaction: float
    time_of_day_bias: str
    news_window_behavior: str
    metadata: Dict[str, Any]

def extract_participant_features(frame) -> ParticipantFeatureVector:
    """
    Deterministically extract microstructure features from a DecisionFrame.
    Assumes frame provides required fields or methods for feature computation.
    """
    # Example field access; replace with actual frame logic as needed
    # All calculations must be deterministic and schema-safe
    aggressive_orders = getattr(frame, 'aggressive_orders', 0)
    time_window = getattr(frame, 'time_window', 1.0)
    orderflow_velocity = aggressive_orders / max(time_window, 1e-9)

    sweep_events = getattr(frame, 'sweep_events', [])
    sweep_intensity = sum(e['size'] for e in sweep_events) / max(time_window, 1e-9)

    passive_fill_volume = getattr(frame, 'passive_fill_volume', 0.0)
    aggressive_volume = getattr(frame, 'aggressive_volume', 1e-9)
    absorption_ratio = passive_fill_volume / aggressive_volume

    bid_pressure = getattr(frame, 'bid_pressure', 0.0)
    ask_pressure = getattr(frame, 'ask_pressure', 0.0)
    spread_pressure = (bid_pressure - ask_pressure) / max(abs(bid_pressure) + abs(ask_pressure), 1e-9)

    book_depletion = getattr(frame, 'book_depletion', 0.0)
    liquidity_removal_rate = book_depletion / max(time_window, 1e-9)

    short_vol = getattr(frame, 'short_horizon_vol', 0.0)
    baseline_vol = getattr(frame, 'baseline_vol', 1e-9)
    volatility_reaction = short_vol / baseline_vol

    tod = getattr(frame, 'time_of_day', 'all_day')
    if tod in {'open', 'mid', 'close', 'all_day'}:
        time_of_day_bias = tod
    else:
        time_of_day_bias = 'all_day'

    news_flag = getattr(frame, 'news_window', 'none')
    if news_flag in {'pre', 'during', 'post', 'none'}:
        news_window_behavior = news_flag
    else:
        news_window_behavior = 'none'

    metadata = {
        'source': 'extract_participant_features',
        'frame_id': getattr(frame, 'frame_id', None)
    }

    return ParticipantFeatureVector(
        orderflow_velocity=orderflow_velocity,
        sweep_intensity=sweep_intensity,
        absorption_ratio=absorption_ratio,
        spread_pressure=spread_pressure,
        liquidity_removal_rate=liquidity_removal_rate,
        volatility_reaction=volatility_reaction,
        time_of_day_bias=time_of_day_bias,
        news_window_behavior=news_window_behavior,
        metadata=metadata,
    )
