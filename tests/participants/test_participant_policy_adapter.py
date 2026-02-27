import pytest
from engine.participants.participant_policy_adapter import (
    adjust_template_policy_by_participants,
    adjust_entry_policy_by_participants,
)
from engine.participants.participant_likelihood_model import ParticipantLikelihood, ParticipantType
import copy

def make_likelihoods(mapping):
    return [ParticipantLikelihood(type=ParticipantType[k], probability=v, evidence={}) for k, v in mapping.items()]

def test_deterministic_adjustment_template():
    base = {
        'mean_reversion_weight': 1.0,
        'breakout_weight': 1.0,
        'sweep_reversal_weight': 1.0,
        'thin_liquidity_weight': 1.0,
        'trend_continuation_weight': 1.0,
        'counter_trend_weight': 1.0,
        'continuation_during_news': True,
        'breakout_caution_weight': 1.0,
        'reversal_weight': 1.0,
        'path_count': 10,
        'noise_tolerance': 0.1,
    }
    orig = copy.deepcopy(base)
    likelihoods = make_likelihoods({'MARKET_MAKER': 0.2, 'SWEEP_BOT': 0.2, 'FUND': 0.2, 'NEWS_ALGO': 0.2, 'LIQUIDITY_HUNTER': 0.2, 'RETAIL': 0.2})
    adjusted, meta = adjust_template_policy_by_participants(base, likelihoods)
    # Check deterministic
    adjusted2, meta2 = adjust_template_policy_by_participants(base, likelihoods)
    assert adjusted == adjusted2
    assert meta == meta2
    # Check no mutation
    assert base == orig
    # Check ordering
    assert list(adjusted.keys()) == list(base.keys())
    # Check directional influence
    assert adjusted['mean_reversion_weight'] > base['mean_reversion_weight']
    assert adjusted['breakout_weight'] < base['breakout_weight']
    assert adjusted['sweep_reversal_weight'] > base['sweep_reversal_weight']
    assert adjusted['thin_liquidity_weight'] < base['thin_liquidity_weight']
    assert adjusted['trend_continuation_weight'] > base['trend_continuation_weight']
    assert adjusted['counter_trend_weight'] < base['counter_trend_weight']
    assert adjusted['continuation_during_news'] is False
    assert adjusted['breakout_caution_weight'] > base['breakout_caution_weight']
    assert adjusted['reversal_weight'] > base['reversal_weight']
    assert adjusted['path_count'] > base['path_count']
    assert adjusted['noise_tolerance'] > base['noise_tolerance']
    # Check metadata
    for k, v in meta.items():
        assert isinstance(v, bool)

def test_deterministic_adjustment_entry():
    base = {
        'mean_reversion_entry': 1.0,
        'breakout_entry': 1.0,
        'sweep_reversal_entry': 1.0,
        'thin_liquidity_entry': 1.0,
        'trend_continuation_entry': 1.0,
        'counter_trend_entry': 1.0,
        'continuation_entry_during_news': True,
        'breakout_caution_entry': 1.0,
        'reversal_entry': 1.0,
        'path_count': 10,
        'noise_tolerance': 0.1,
    }
    orig = copy.deepcopy(base)
    likelihoods = make_likelihoods({'MARKET_MAKER': 0.2, 'SWEEP_BOT': 0.2, 'FUND': 0.2, 'NEWS_ALGO': 0.2, 'LIQUIDITY_HUNTER': 0.2, 'RETAIL': 0.2})
    adjusted, meta = adjust_entry_policy_by_participants(base, likelihoods)
    # Check deterministic
    adjusted2, meta2 = adjust_entry_policy_by_participants(base, likelihoods)
    assert adjusted == adjusted2
    assert meta == meta2
    # Check no mutation
    assert base == orig
    # Check ordering
    assert list(adjusted.keys()) == list(base.keys())
    # Check directional influence
    assert adjusted['mean_reversion_entry'] > base['mean_reversion_entry']
    assert adjusted['breakout_entry'] < base['breakout_entry']
    assert adjusted['sweep_reversal_entry'] > base['sweep_reversal_entry']
    assert adjusted['thin_liquidity_entry'] < base['thin_liquidity_entry']
    assert adjusted['trend_continuation_entry'] > base['trend_continuation_entry']
    assert adjusted['counter_trend_entry'] < base['counter_trend_entry']
    assert adjusted['continuation_entry_during_news'] is False
    assert adjusted['breakout_caution_entry'] > base['breakout_caution_entry']
    assert adjusted['reversal_entry'] > base['reversal_entry']
    assert adjusted['path_count'] > base['path_count']
    assert adjusted['noise_tolerance'] > base['noise_tolerance']
    # Check metadata
    for k, v in meta.items():
        assert isinstance(v, bool)

def test_no_participant_influence():
    base = {
        'mean_reversion_weight': 1.0,
        'breakout_weight': 1.0,
        'sweep_reversal_weight': 1.0,
        'thin_liquidity_weight': 1.0,
        'trend_continuation_weight': 1.0,
        'counter_trend_weight': 1.0,
        'continuation_during_news': True,
        'breakout_caution_weight': 1.0,
        'reversal_weight': 1.0,
        'path_count': 10,
        'noise_tolerance': 0.1,
    }
    orig = copy.deepcopy(base)
    likelihoods = make_likelihoods({'MARKET_MAKER': 0.0, 'SWEEP_BOT': 0.0, 'FUND': 0.0, 'NEWS_ALGO': 0.0, 'LIQUIDITY_HUNTER': 0.0, 'RETAIL': 0.0})
    adjusted, meta = adjust_template_policy_by_participants(base, likelihoods)
    assert adjusted == base
    assert base == orig
    for v in meta.values():
        assert v is False

def test_partial_participant_influence():
    base = {
        'mean_reversion_weight': 1.0,
        'breakout_weight': 1.0,
        'sweep_reversal_weight': 1.0,
        'thin_liquidity_weight': 1.0,
        'trend_continuation_weight': 1.0,
        'counter_trend_weight': 1.0,
        'continuation_during_news': True,
        'breakout_caution_weight': 1.0,
        'reversal_weight': 1.0,
        'path_count': 10,
        'noise_tolerance': 0.1,
    }
    orig = copy.deepcopy(base)
    likelihoods = make_likelihoods({'MARKET_MAKER': 0.2, 'SWEEP_BOT': 0.0, 'FUND': 0.0, 'NEWS_ALGO': 0.0, 'LIQUIDITY_HUNTER': 0.0, 'RETAIL': 0.0})
    adjusted, meta = adjust_template_policy_by_participants(base, likelihoods)
    assert adjusted['mean_reversion_weight'] > base['mean_reversion_weight']
    assert adjusted['breakout_weight'] < base['breakout_weight']
    # Only MARKET_MAKER meta True
    assert meta['market_maker_mean_reversion'] is True
    assert meta['market_maker_breakout_down'] is True
    for k, v in meta.items():
        if k.startswith('market_maker'):
            continue
        assert v is False
    # No mutation
    assert base == orig
    # Ordering
    assert list(adjusted.keys()) == list(base.keys())
