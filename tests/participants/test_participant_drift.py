import pytest
from engine.participants.participant_drift import ParticipantDriftSignal, compute_participant_drift
from engine.participants.participant_taxonomy import ParticipantType

def base_artifacts():
    return {
        ParticipantType.SWEEP_BOT: {
            'sweep_intensity': 1.0,
            'absorption_ratio': 0.5,
            'liquidity_removal_rate': 0.5,
            'volatility_reaction': 0.5,
            'time_of_day_bias': 'mid',
            'news_window_behavior': 'none',
        },
        ParticipantType.MARKET_MAKER: {
            'sweep_intensity': 0.5,
            'absorption_ratio': 1.2,
            'liquidity_removal_rate': 0.5,
            'volatility_reaction': 0.5,
            'time_of_day_bias': 'mid',
            'news_window_behavior': 'none',
        },
        ParticipantType.FUND: {
            'sweep_intensity': 0.5,
            'absorption_ratio': 0.5,
            'liquidity_removal_rate': 0.5,
            'volatility_reaction': 0.5,
            'time_of_day_bias': 'mid',
            'news_window_behavior': 'none',
        },
        ParticipantType.NEWS_ALGO: {
            'sweep_intensity': 0.5,
            'absorption_ratio': 0.5,
            'liquidity_removal_rate': 0.5,
            'volatility_reaction': 0.5,
            'time_of_day_bias': 'mid',
            'news_window_behavior': 'none',
        },
        ParticipantType.RETAIL: {
            'sweep_intensity': 0.5,
            'absorption_ratio': 0.5,
            'liquidity_removal_rate': 0.5,
            'volatility_reaction': 0.5,
            'time_of_day_bias': 'mid',
            'news_window_behavior': 'none',
        },
    }

def test_no_drift():
    before = base_artifacts()
    after = base_artifacts()
    signals = compute_participant_drift(before, after)
    assert signals == []

def test_sweep_intensity_drift():
    before = base_artifacts()
    after = base_artifacts()
    after[ParticipantType.SWEEP_BOT]['sweep_intensity'] = 4.0
    signals = compute_participant_drift(before, after)
    assert any(s.reason == 'sweep_intensity_change' for s in signals)
    assert all(isinstance(s.metadata, dict) for s in signals)
    # Correct severity
    for s in signals:
        if s.reason == 'sweep_intensity_change':
            assert s.severity in {'info', 'warning', 'critical'}

def test_absorption_drift():
    before = base_artifacts()
    after = base_artifacts()
    after[ParticipantType.MARKET_MAKER]['absorption_ratio'] = 2.5
    signals = compute_participant_drift(before, after)
    assert any(s.reason == 'absorption_ratio_change' for s in signals)
    for s in signals:
        if s.reason == 'absorption_ratio_change':
            assert s.severity in {'info', 'warning', 'critical'}

def test_liquidity_removal_drift():
    before = base_artifacts()
    after = base_artifacts()
    after[ParticipantType.FUND]['liquidity_removal_rate'] = 2.0
    signals = compute_participant_drift(before, after)
    assert any(s.reason == 'liquidity_removal_rate_change' for s in signals)

def test_volatility_reaction_drift():
    before = base_artifacts()
    after = base_artifacts()
    after[ParticipantType.RETAIL]['volatility_reaction'] = 1.2
    signals = compute_participant_drift(before, after)
    assert any(s.reason == 'volatility_reaction_change' for s in signals)

def test_time_of_day_bias_drift():
    before = base_artifacts()
    after = base_artifacts()
    after[ParticipantType.RETAIL]['time_of_day_bias'] = 'open'
    signals = compute_participant_drift(before, after)
    assert any(s.reason == 'time_of_day_bias_change' for s in signals)

def test_news_window_behavior_drift():
    before = base_artifacts()
    after = base_artifacts()
    after[ParticipantType.NEWS_ALGO]['news_window_behavior'] = 'during'
    signals = compute_participant_drift(before, after)
    assert any(s.reason == 'news_window_behavior_change' for s in signals)

def test_sweep_bot_dominance():
    before = base_artifacts()
    after = base_artifacts()
    after[ParticipantType.SWEEP_BOT]['sweep_intensity'] = 6.0
    signals = compute_participant_drift(before, after)
    assert any(s.reason == 'sweep_bot_dominance' and s.severity == 'critical' for s in signals)

def test_market_maker_withdrawal():
    before = base_artifacts()
    after = base_artifacts()
    before[ParticipantType.MARKET_MAKER]['absorption_ratio'] = 1.5
    after[ParticipantType.MARKET_MAKER]['absorption_ratio'] = 0.1
    signals = compute_participant_drift(before, after)
    assert any(s.reason == 'market_maker_withdrawal' and s.severity == 'critical' for s in signals)

def test_fund_aggression_spike():
    before = base_artifacts()
    after = base_artifacts()
    before[ParticipantType.FUND]['liquidity_removal_rate'] = 0.5
    after[ParticipantType.FUND]['liquidity_removal_rate'] = 3.5
    signals = compute_participant_drift(before, after)
    assert any(s.reason == 'fund_aggression_spike' and s.severity == 'critical' for s in signals)

def test_news_algo_takeover():
    before = base_artifacts()
    after = base_artifacts()
    before[ParticipantType.NEWS_ALGO]['news_window_behavior'] = 'none'
    after[ParticipantType.NEWS_ALGO]['news_window_behavior'] = 'during'
    signals = compute_participant_drift(before, after)
    assert any(s.reason == 'news_algo_takeover' and s.severity == 'critical' for s in signals)

def test_retail_surge():
    before = base_artifacts()
    after = base_artifacts()
    before[ParticipantType.RETAIL]['time_of_day_bias'] = 'mid'
    after[ParticipantType.RETAIL]['time_of_day_bias'] = 'open'
    signals = compute_participant_drift(before, after)
    assert any(s.reason == 'retail_surge' and s.severity == 'critical' for s in signals)

def test_deterministic_ordering():
    before = base_artifacts()
    after = base_artifacts()
    after[ParticipantType.SWEEP_BOT]['sweep_intensity'] = 4.0
    after[ParticipantType.MARKET_MAKER]['absorption_ratio'] = 2.5
    after[ParticipantType.FUND]['liquidity_removal_rate'] = 2.0
    signals = compute_participant_drift(before, after)
    # Should be sorted by (severity, participant_type.name, reason)
    keys = [(s.severity, s.participant_type.name, s.reason) for s in signals]
    assert keys == sorted(keys)

def test_metadata_correctness():
    before = base_artifacts()
    after = base_artifacts()
    after[ParticipantType.SWEEP_BOT]['sweep_intensity'] = 4.0
    signals = compute_participant_drift(before, after)
    for s in signals:
        assert isinstance(s.metadata, dict)
