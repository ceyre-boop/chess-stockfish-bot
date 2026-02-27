import copy
import pytest
from engine.brain.ev_participant_adapter import build_ev_features_with_participants
from engine.participants.participant_taxonomy import ParticipantType
from engine.participants.participant_likelihood_model import ParticipantLikelihood

def make_likelihoods():
    # Deterministic, simple spread
    return [
        ParticipantLikelihood(type=ParticipantType.RETAIL, probability=0.1, evidence={}),
        ParticipantLikelihood(type=ParticipantType.ALGO, probability=0.2, evidence={}),
        ParticipantLikelihood(type=ParticipantType.MARKET_MAKER, probability=0.15, evidence={}),
        ParticipantLikelihood(type=ParticipantType.FUND, probability=0.1, evidence={}),
        ParticipantLikelihood(type=ParticipantType.NEWS_ALGO, probability=0.25, evidence={}),
        ParticipantLikelihood(type=ParticipantType.LIQUIDITY_HUNTER, probability=0.1, evidence={}),
        ParticipantLikelihood(type=ParticipantType.SWEEP_BOT, probability=0.1, evidence={}),
    ]

def test_deterministic_extension():
    base = {"foo": 1, "bar": 2}
    lik = make_likelihoods()
    out1 = build_ev_features_with_participants(base, None, lik)
    out2 = build_ev_features_with_participants(base, None, lik)
    assert out1 == out2
    assert out1 is not base

def test_one_hot_mapping():
    base = {}
    lik = make_likelihoods()
    out = build_ev_features_with_participants(base, None, lik)
    for l in lik:
        k = f"participant_{l.type.name.lower()}_prob"
        assert k in out
        assert abs(out[k] - l.probability) < 1e-8

def test_aggregate_signals():
    base = {}
    lik = make_likelihoods()
    out = build_ev_features_with_participants(base, None, lik)
    assert abs(out["participant_sweep_risk"] - (0.1 + 0.1)) < 1e-8
    assert abs(out["participant_mm_presence"] - 0.15) < 1e-8
    assert abs(out["participant_fund_pressure"] - 0.1) < 1e-8
    assert abs(out["participant_news_algo_pressure"] - 0.25) < 1e-8

def test_base_ev_features_unchanged():
    base = {"foo": 1, "bar": 2}
    base_copy = copy.deepcopy(base)
    lik = make_likelihoods()
    _ = build_ev_features_with_participants(base, None, lik)
    assert base == base_copy

def test_stable_key_ordering():
    base = {"z": 1, "a": 2}
    lik = make_likelihoods()
    out = build_ev_features_with_participants(base, None, lik)
    keys = list(out.keys())
    assert keys == sorted(keys)
