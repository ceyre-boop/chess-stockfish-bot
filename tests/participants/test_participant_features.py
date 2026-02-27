import pytest
from engine.participants.participant_features import (
    ParticipantFeatureVector, extract_participant_features)

class DummyFrame:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

def test_deterministic_extraction():
    frame = DummyFrame(
        aggressive_orders=10,
        time_window=5.0,
        sweep_events=[{'size': 20}, {'size': 10}],
        passive_fill_volume=30.0,
        aggressive_volume=15.0,
        bid_pressure=100.0,
        ask_pressure=80.0,
        book_depletion=25.0,
        short_horizon_vol=2.0,
        baseline_vol=1.0,
        time_of_day='open',
        news_window='pre',
        frame_id='abc123',
    )
    v1 = extract_participant_features(frame)
    v2 = extract_participant_features(frame)
    assert v1 == v2
    assert isinstance(v1, ParticipantFeatureVector)
    assert v1.metadata['source'] == 'extract_participant_features'
    assert v1.metadata['frame_id'] == 'abc123'

def test_feature_computation():
    frame = DummyFrame(
        aggressive_orders=20,
        time_window=4.0,
        sweep_events=[{'size': 8}, {'size': 12}],
        passive_fill_volume=40.0,
        aggressive_volume=20.0,
        bid_pressure=60.0,
        ask_pressure=40.0,
        book_depletion=16.0,
        short_horizon_vol=3.0,
        baseline_vol=1.5,
        time_of_day='mid',
        news_window='during',
        frame_id='f2',
    )
    v = extract_participant_features(frame)
    assert abs(v.orderflow_velocity - 5.0) < 1e-6
    assert abs(v.sweep_intensity - 5.0) < 1e-6
    assert abs(v.absorption_ratio - 2.0) < 1e-6
    assert abs(v.spread_pressure - 0.2) < 1e-6
    assert abs(v.liquidity_removal_rate - 4.0) < 1e-6
    assert abs(v.volatility_reaction - 2.0) < 1e-6
    assert v.time_of_day_bias == 'mid'
    assert v.news_window_behavior == 'during'
    assert isinstance(v.metadata, dict)

def test_time_of_day_classification():
    for tod in ['open', 'mid', 'close', 'all_day', 'weird']:
        frame = DummyFrame(time_of_day=tod)
        v = extract_participant_features(frame)
        if tod in {'open', 'mid', 'close', 'all_day'}:
            assert v.time_of_day_bias == tod
        else:
            assert v.time_of_day_bias == 'all_day'

def test_news_window_classification():
    for nw in ['pre', 'during', 'post', 'none', 'strange']:
        frame = DummyFrame(news_window=nw)
        v = extract_participant_features(frame)
        if nw in {'pre', 'during', 'post', 'none'}:
            assert v.news_window_behavior == nw
        else:
            assert v.news_window_behavior == 'none'

def test_metadata_schema():
    frame = DummyFrame(frame_id='meta1')
    v = extract_participant_features(frame)
    assert isinstance(v.metadata, dict)
    assert 'source' in v.metadata
    assert v.metadata['source'] == 'extract_participant_features'
