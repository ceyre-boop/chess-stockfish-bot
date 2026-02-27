from engine.participants.participant_taxonomy import ParticipantType
from typing import Any, Dict, List

def build_ev_features_with_participants(frame: Any, action: Any, participant_likelihoods: List) -> Dict:
    """
    Extend base EV features with participant likelihood signals.
    Does not mutate input frame or base EV features.
    Returns a new dict with sorted keys.
    """
    # Assume frame is the base EV feature dict
    base = dict(frame)  # shallow copy, do not mutate input
    ev_features = dict(base)

    # One-hot participant probabilities
    for likelihood in participant_likelihoods:
        key = f"participant_{likelihood.type.name.lower()}_prob"
        ev_features[key] = likelihood.probability

    # Aggregate signals
    pt = {l.type: l.probability for l in participant_likelihoods}
    ev_features["participant_sweep_risk"] = pt.get(ParticipantType.SWEEP_BOT, 0.0) + pt.get(ParticipantType.LIQUIDITY_HUNTER, 0.0)
    ev_features["participant_mm_presence"] = pt.get(ParticipantType.MARKET_MAKER, 0.0)
    ev_features["participant_fund_pressure"] = pt.get(ParticipantType.FUND, 0.0)
    ev_features["participant_news_algo_pressure"] = pt.get(ParticipantType.NEWS_ALGO, 0.0)

    # Return with stable ordering
    return dict(sorted(ev_features.items()))
