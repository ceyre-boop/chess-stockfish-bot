from dataclasses import dataclass, field
from typing import List, Dict, Any
from engine.participants.participant_taxonomy import ParticipantType

@dataclass(frozen=True)
class ParticipantDriftSignal:
    participant_type: ParticipantType
    severity: str  # "info", "warning", "critical"
    reason: str
    before: Dict[str, Any]
    after: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

def compute_participant_drift(before_artifacts: Dict[ParticipantType, Dict[str, Any]], after_artifacts: Dict[ParticipantType, Dict[str, Any]]) -> List[ParticipantDriftSignal]:
    signals = []
    for ptype in sorted(set(before_artifacts.keys()) | set(after_artifacts.keys()), key=lambda x: x.name):
        before = before_artifacts.get(ptype, {})
        after = after_artifacts.get(ptype, {})
        meta = {}
        # Sweep intensity drift
        b_sweep = before.get('sweep_intensity', 0.0)
        a_sweep = after.get('sweep_intensity', 0.0)
        sweep_delta = a_sweep - b_sweep
        if abs(sweep_delta) > 2.5:
            sev = 'critical'
        elif abs(sweep_delta) > 1.0:
            sev = 'warning'
        elif abs(sweep_delta) > 0.3:
            sev = 'info'
        else:
            sev = None
        if sev:
            reason = 'sweep_intensity_change'
            meta['delta'] = sweep_delta
            signals.append(ParticipantDriftSignal(ptype, sev, reason, before, after, meta))
        # Absorption drift
        b_abs = before.get('absorption_ratio', 0.0)
        a_abs = after.get('absorption_ratio', 0.0)
        abs_delta = a_abs - b_abs
        if abs(abs_delta) > 1.0:
            sev = 'critical'
        elif abs(abs_delta) > 0.4:
            sev = 'warning'
        elif abs(abs_delta) > 0.1:
            sev = 'info'
        else:
            sev = None
        if sev:
            reason = 'absorption_ratio_change'
            meta = {'delta': abs_delta}
            signals.append(ParticipantDriftSignal(ptype, sev, reason, before, after, meta))
        # Liquidity removal drift
        b_liq = before.get('liquidity_removal_rate', 0.0)
        a_liq = after.get('liquidity_removal_rate', 0.0)
        liq_delta = a_liq - b_liq
        if abs(liq_delta) > 2.0:
            sev = 'critical'
        elif abs(liq_delta) > 0.8:
            sev = 'warning'
        elif abs(liq_delta) > 0.2:
            sev = 'info'
        else:
            sev = None
        if sev:
            reason = 'liquidity_removal_rate_change'
            meta = {'delta': liq_delta}
            signals.append(ParticipantDriftSignal(ptype, sev, reason, before, after, meta))
        # Volatility reaction drift
        b_vol = before.get('volatility_reaction', 0.0)
        a_vol = after.get('volatility_reaction', 0.0)
        vol_delta = a_vol - b_vol
        if abs(vol_delta) > 1.0:
            sev = 'critical'
        elif abs(vol_delta) > 0.4:
            sev = 'warning'
        elif abs(vol_delta) > 0.1:
            sev = 'info'
        else:
            sev = None
        if sev:
            reason = 'volatility_reaction_change'
            meta = {'delta': vol_delta}
            signals.append(ParticipantDriftSignal(ptype, sev, reason, before, after, meta))
        # Time-of-day bias drift
        b_tod = before.get('time_of_day_bias', None)
        a_tod = after.get('time_of_day_bias', None)
        if b_tod != a_tod and (b_tod is not None or a_tod is not None):
            sev = 'warning' if b_tod and a_tod else 'info'
            reason = 'time_of_day_bias_change'
            meta = {'before': b_tod, 'after': a_tod}
            signals.append(ParticipantDriftSignal(ptype, sev, reason, before, after, meta))
        # News window behavior drift
        b_news = before.get('news_window_behavior', None)
        a_news = after.get('news_window_behavior', None)
        if b_news != a_news and (b_news is not None or a_news is not None):
            sev = 'warning' if b_news and a_news else 'info'
            reason = 'news_window_behavior_change'
            meta = {'before': b_news, 'after': a_news}
            signals.append(ParticipantDriftSignal(ptype, sev, reason, before, after, meta))
        # Misalignment: sudden sweep-bot dominance
        if ptype.name == 'SWEEP_BOT' and b_sweep < 2.0 and a_sweep > 5.0:
            reason = 'sweep_bot_dominance'
            sev = 'critical'
            meta = {'before': b_sweep, 'after': a_sweep}
            signals.append(ParticipantDriftSignal(ptype, sev, reason, before, after, meta))
        # MM withdrawal
        if ptype.name == 'MARKET_MAKER' and b_abs > 1.0 and a_abs < 0.2:
            reason = 'market_maker_withdrawal'
            sev = 'critical'
            meta = {'before': b_abs, 'after': a_abs}
            signals.append(ParticipantDriftSignal(ptype, sev, reason, before, after, meta))
        # Fund aggression spike
        if ptype.name == 'FUND' and b_liq < 1.0 and a_liq > 3.0:
            reason = 'fund_aggression_spike'
            sev = 'critical'
            meta = {'before': b_liq, 'after': a_liq}
            signals.append(ParticipantDriftSignal(ptype, sev, reason, before, after, meta))
        # News-algo takeover
        if ptype.name == 'NEWS_ALGO' and b_news != 'during' and a_news == 'during':
            reason = 'news_algo_takeover'
            sev = 'critical'
            meta = {'before': b_news, 'after': a_news}
            signals.append(ParticipantDriftSignal(ptype, sev, reason, before, after, meta))
        # Retail surge
        if ptype.name == 'RETAIL' and b_tod != 'open' and a_tod == 'open':
            reason = 'retail_surge'
            sev = 'critical'
            meta = {'before': b_tod, 'after': a_tod}
            signals.append(ParticipantDriftSignal(ptype, sev, reason, before, after, meta))
    # Deterministic sort: (severity, participant_type.name, reason)
    severity_order = {'critical': 0, 'warning': 1, 'info': 2}
    signals.sort(key=lambda s: (severity_order[s.severity], s.participant_type.name, s.reason))
    return signals
