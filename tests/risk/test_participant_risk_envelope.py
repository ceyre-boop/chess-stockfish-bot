import pytest
from engine.risk.participant_risk_envelope import (
    ParticipantRiskLimits,
    get_participant_risk_limits,
    enforce_participant_risk,
)
from engine.participants.participant_likelihood_model import ParticipantLikelihood, ParticipantType
import copy

def make_likelihoods(mapping):
    return [ParticipantLikelihood(type=ParticipantType[k], probability=v, evidence={}) for k, v in mapping.items()]

def base_frame():
    return {
        'max_size': 100,
        'max_concurrent_risk': 50,
        'max_daily_risk': 200,
    }

def base_action():
    return {
        'size': 100,
        'concurrent_risk': 50,
        'daily_risk': 200,
        'no_trade': False,
    }

def test_deterministic_limits():
    likelihoods = make_likelihoods({'SWEEP_BOT': 0.2, 'LIQUIDITY_HUNTER': 0.2, 'MARKET_MAKER': 0.2, 'FUND': 0.2, 'NEWS_ALGO': 0.2, 'RETAIL': 0.2})
    limits1 = get_participant_risk_limits(likelihoods)
    limits2 = get_participant_risk_limits(likelihoods)
    assert limits1 == limits2
    assert isinstance(limits1.metadata, dict)
    for v in limits1.metadata.values():
        assert isinstance(v, bool)

def test_sweep_bot_reduces_size():
    likelihoods = make_likelihoods({'SWEEP_BOT': 0.2})
    limits = get_participant_risk_limits(likelihoods)
    assert limits.max_size_multiplier < 1.0
    assert limits.metadata['sweep_bot_caution'] is True

def test_liquidity_hunter_reduces_size():
    likelihoods = make_likelihoods({'LIQUIDITY_HUNTER': 0.2})
    limits = get_participant_risk_limits(likelihoods)
    assert limits.max_size_multiplier < 1.0
    assert limits.metadata['liquidity_hunter_caution'] is True

def test_market_maker_wider_stops():
    likelihoods = make_likelihoods({'MARKET_MAKER': 0.2})
    limits = get_participant_risk_limits(likelihoods)
    assert limits.max_concurrent_risk > 1.0 and limits.max_concurrent_risk <= 1.1
    assert limits.metadata['market_maker_wider_stops'] is True

def test_fund_reduces_leverage():
    likelihoods = make_likelihoods({'FUND': 0.2})
    limits = get_participant_risk_limits(likelihoods)
    assert limits.max_size_multiplier < 1.0
    assert limits.metadata['fund_reduce_leverage'] is True

def test_news_algo_no_trade():
    likelihoods = make_likelihoods({'NEWS_ALGO': 0.2})
    limits = get_participant_risk_limits(likelihoods)
    assert limits.no_trade is True
    assert limits.metadata['news_algo_no_trade'] is True

def test_retail_noise_tolerance():
    likelihoods = make_likelihoods({'RETAIL': 0.2})
    limits = get_participant_risk_limits(likelihoods)
    assert limits.metadata['retail_noise_tolerance'] is True
    # Never increases risk caps
    assert limits.max_size_multiplier <= 1.0
    assert limits.max_concurrent_risk <= 1.0
    assert limits.max_daily_risk <= 1.0

def test_enforce_no_mutation():
    frame = base_frame()
    action = base_action()
    orig_action = copy.deepcopy(action)
    likelihoods = make_likelihoods({'SWEEP_BOT': 0.2})
    limits = get_participant_risk_limits(likelihoods)
    enforced = enforce_participant_risk(frame, action, likelihoods, limits)
    assert action == orig_action
    # Returns new object
    assert enforced is not action

def test_enforce_respects_caps():
    frame = base_frame()
    action = base_action()
    likelihoods = make_likelihoods({'SWEEP_BOT': 0.2})
    limits = get_participant_risk_limits(likelihoods)
    enforced = enforce_participant_risk(frame, action, likelihoods, limits)
    # Size never exceeds cap
    assert enforced['size'] <= frame['max_size']
    assert enforced['concurrent_risk'] <= frame['max_concurrent_risk']
    assert enforced['daily_risk'] <= frame['max_daily_risk']

def test_enforce_news_algo_no_trade():
    frame = base_frame()
    action = base_action()
    likelihoods = make_likelihoods({'NEWS_ALGO': 0.2})
    limits = get_participant_risk_limits(likelihoods)
    enforced = enforce_participant_risk(frame, action, likelihoods, limits)
    assert enforced['no_trade'] is True
    assert enforced['participant_risk_metadata']['news_algo_no_trade'] is True

def test_enforce_sweep_bot_reduces_size():
    frame = base_frame()
    action = base_action()
    likelihoods = make_likelihoods({'SWEEP_BOT': 0.2})
    limits = get_participant_risk_limits(likelihoods)
    enforced = enforce_participant_risk(frame, action, likelihoods, limits)
    assert enforced['size'] < action['size']
    assert enforced['participant_risk_metadata']['sweep_bot_caution'] is True

def test_enforce_market_maker_wider_stop():
    frame = base_frame()
    action = base_action()
    likelihoods = make_likelihoods({'MARKET_MAKER': 0.2})
    limits = get_participant_risk_limits(likelihoods)
    enforced = enforce_participant_risk(frame, action, likelihoods, limits)
    assert enforced['concurrent_risk'] <= frame['max_concurrent_risk']
    assert enforced['participant_risk_metadata']['market_maker_wider_stops'] is True
    # Still respects cap
    assert enforced['concurrent_risk'] <= frame['max_concurrent_risk']

def test_metadata_stable_and_correct():
    likelihoods = make_likelihoods({'SWEEP_BOT': 0.2, 'NEWS_ALGO': 0.2})
    limits = get_participant_risk_limits(likelihoods)
    frame = base_frame()
    action = base_action()
    enforced = enforce_participant_risk(frame, action, likelihoods, limits)
    meta = enforced['participant_risk_metadata']
    # All meta keys present and stable
    assert 'sweep_bot_caution' in meta
    assert 'news_algo_no_trade' in meta
    assert isinstance(meta['sweep_bot_caution'], bool)
    assert isinstance(meta['news_algo_no_trade'], bool)
    # Ordering
    assert list(enforced.keys()) == list(action.keys()) + ['participant_risk_metadata']
