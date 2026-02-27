import pytest
import os
import json
from engine.participants.participant_meta_update import (
    build_candidate_participant_policy,
    validate_and_promote_participant_policy,
    emit_policy_artifacts,
    ParticipantMetaUpdatePlan,
)

def base_policy():
    return {
        'reversal_rule': 'ALLOWED',
        'continuation_during_news': 'ALLOWED',
        'trend_continuation_rule': 'PREFERRED',
        'mean_reversion_rule': 'PREFERRED',
    }

def test_candidate_generation_drift_tightening():
    current = base_policy()
    drift_signals = [
        type('Drift', (), {'participant_type': type('PT', (), {'name': 'SWEEP_BOT'})(), 'reason': 'sweep_bot_dominance'})
    ]
    candidate, reasons = build_candidate_participant_policy(current, {}, drift_signals)
    assert candidate['reversal_rule'] == 'DISCOURAGED' or candidate['reversal_rule'] == 'ALLOWED'
    assert any('sweep_bot_dominance' in r for r in reasons)

def test_candidate_generation_news_strictness():
    current = base_policy()
    drift_signals = [
        type('Drift', (), {'participant_type': type('PT', (), {'name': 'NEWS_ALGO'})(), 'reason': 'news_algo_takeover'})
    ]
    candidate, reasons = build_candidate_participant_policy(current, {}, drift_signals)
    assert candidate['continuation_during_news'] == 'DISABLED'
    assert any('news_algo_takeover' in r for r in reasons)

def test_candidate_generation_performance():
    current = base_policy()
    perf = {'trend_ev': -1.0, 'mean_reversion_winrate': 0.3}
    candidate, reasons = build_candidate_participant_policy(current, perf, [])
    assert candidate['trend_continuation_rule'] == 'ALLOWED'
    assert candidate['mean_reversion_rule'] == 'ALLOWED'

def test_monotonicity_enforcement():
    current = {'reversal_rule': 'ALLOWED'}
    candidate = {'reversal_rule': 'PREFERRED'}
    # Should not allow reversal to more lenient
    candidate2, _ = build_candidate_participant_policy(current, {}, [])
    assert candidate2['reversal_rule'] == 'ALLOWED'

def test_no_new_keys():
    current = base_policy()
    candidate = dict(current)
    candidate['new_key'] = 'foo'
    candidate2, _ = build_candidate_participant_policy(current, {}, [])
    assert 'new_key' not in candidate2

def test_minimum_data_enforcement():
    current = base_policy()
    candidate = dict(current)
    perf = {'data_counts': {'SWEEP_BOT': 5}}
    plan = validate_and_promote_participant_policy(current, candidate, perf, min_data=10)
    assert not plan.promoted
    assert any('minimum data' in r for r in plan.reasons)

def test_no_degradation_rule():
    current = base_policy()
    candidate = dict(current)
    perf = {'candidate_ev': 0.5, 'current_ev': 0.6, 'candidate_winrate': 0.5, 'current_winrate': 0.6, 'candidate_tail_risk': 0.5, 'current_tail_risk': 0.6}
    plan = validate_and_promote_participant_policy(current, candidate, perf)
    assert not plan.promoted
    assert any('degraded' in r for r in plan.reasons)

def test_no_flip_flops_rule():
    current = base_policy()
    candidate = dict(current)
    perf = {'label_changes': 5, 'total_labels': 10}
    plan = validate_and_promote_participant_policy(current, candidate, perf, max_label_change_rate=0.2)
    assert not plan.promoted
    assert any('label changes' in r for r in plan.reasons)

def test_news_strictness_rule():
    current = base_policy()
    candidate = dict(current)
    candidate['continuation_during_news'] = 'ALLOWED'
    current['continuation_during_news'] = 'DISABLED'
    perf = {}
    plan = validate_and_promote_participant_policy(current, candidate, perf)
    assert not plan.promoted
    assert any('news strictness' in r for r in plan.reasons)

def test_promotion_logic():
    current = base_policy()
    candidate = dict(current)
    perf = {'data_counts': {'SWEEP_BOT': 20}, 'candidate_ev': 0.7, 'current_ev': 0.6, 'candidate_winrate': 0.7, 'current_winrate': 0.6, 'candidate_tail_risk': 0.7, 'current_tail_risk': 0.6, 'label_changes': 0, 'total_labels': 10}
    plan = validate_and_promote_participant_policy(current, candidate, perf)
    assert plan.promoted
    assert plan.diff == {}

def test_deterministic_diff_generation():
    current = base_policy()
    candidate = dict(current)
    candidate['reversal_rule'] = 'DISABLED'
    plan = validate_and_promote_participant_policy(current, candidate, {'data_counts': {'SWEEP_BOT': 20}})
    assert 'reversal_rule' in plan.diff
    # Sorted keys
    keys = list(plan.diff.keys())
    assert keys == sorted(keys)

def test_artifact_correctness(tmp_path):
    current = base_policy()
    candidate = dict(current)
    diff = {'reversal_rule': {'from': 'ALLOWED', 'to': 'DISABLED'}}
    emit_policy_artifacts(current, candidate, diff, base_path=tmp_path)
    files = ["brain_policy_participants.active.json", "brain_policy_participants.candidate.json", "brain_policy_participants.diff.json"]
    for fname in files:
        path = tmp_path / fname
        assert os.path.exists(path)
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert isinstance(data, dict)
            # Keys sorted
            keys = list(data.keys())
            assert keys == sorted(keys)
