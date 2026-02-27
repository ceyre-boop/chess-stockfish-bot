from dataclasses import dataclass, field
from typing import List, Dict, Any
import copy
import json
from collections import OrderedDict

@dataclass(frozen=True)
class ParticipantMetaUpdatePlan:
    candidate_policy: dict
    promoted: bool
    reasons: List[str]
    diff: dict
    metadata: dict = field(default_factory=dict)

def build_candidate_participant_policy(current_policy, performance_artifacts, drift_signals):
    # Do not mutate current_policy
    candidate = copy.deepcopy(current_policy)
    reasons = []
    drift_map = { (s.participant_type.name, s.reason): s for s in drift_signals }
    # Drift-driven tightening
    for key, value in current_policy.items():
        # Example: sweep-bot dominance → stricter reversal
        if key == 'reversal_rule' and ('SWEEP_BOT', 'sweep_bot_dominance') in drift_map:
            if value == 'ALLOWED':
                candidate[key] = 'DISCOURAGED'
                reasons.append('sweep_bot_dominance: tighten reversal_rule')
            elif value == 'PREFERRED':
                candidate[key] = 'ALLOWED'
                reasons.append('sweep_bot_dominance: tighten reversal_rule')
        # News-algo strictness
        if key == 'continuation_during_news' and ('NEWS_ALGO', 'news_algo_takeover') in drift_map:
            if value != 'DISABLED':
                candidate[key] = 'DISABLED'
                reasons.append('news_algo_takeover: disable continuation during news')
        # Performance-driven: trend continuation
        if key == 'trend_continuation_rule' and performance_artifacts.get('trend_ev', 0) < 0.0:
            if value == 'PREFERRED':
                candidate[key] = 'ALLOWED'
                reasons.append('trend_ev negative: relax trend_continuation_rule')
        # Performance-driven: mean reversion
        if key == 'mean_reversion_rule' and performance_artifacts.get('mean_reversion_winrate', 1.0) < 0.4:
            if value == 'PREFERRED':
                candidate[key] = 'ALLOWED'
                reasons.append('mean_reversion winrate low: relax mean_reversion_rule')
    # Enforce monotonicity: never reverse direction
    order = ['PREFERRED', 'ALLOWED', 'DISCOURAGED', 'DISABLED']
    for k, v in candidate.items():
        if k in current_policy and order.index(candidate[k]) < order.index(current_policy[k]):
            candidate[k] = current_policy[k]
    # Never introduce new keys
    candidate = {k: candidate[k] for k in current_policy.keys()}
    return copy.deepcopy(candidate), reasons

def validate_and_promote_participant_policy(current_policy, candidate_policy, performance_artifacts, min_data=10, max_label_change_rate=0.2):
    reasons = []
    promoted = True
    metadata = {}
    # Minimum data per participant type
    for ptype, data in performance_artifacts.get('data_counts', {}).items():
        if data < min_data:
            promoted = False
            reasons.append(f'minimum data not met for {ptype}')
    # No degradation in key metrics
    for metric in ['ev', 'winrate', 'tail_risk']:
        if performance_artifacts.get(f'candidate_{metric}', 0) < performance_artifacts.get(f'current_{metric}', 0):
            promoted = False
            reasons.append(f'{metric} degraded')
    # No flip-flops
    label_changes = performance_artifacts.get('label_changes', 0)
    total_labels = performance_artifacts.get('total_labels', 1)
    if total_labels > 0 and (label_changes / total_labels) > max_label_change_rate:
        promoted = False
        reasons.append('too many label changes')
    # News strictness
    if 'continuation_during_news' in candidate_policy and 'continuation_during_news' in current_policy:
        order = ['PREFERRED', 'ALLOWED', 'DISCOURAGED', 'DISABLED']
        if order.index(candidate_policy['continuation_during_news']) < order.index(current_policy['continuation_during_news']):
            promoted = False
            reasons.append('news strictness violated')
    # Deterministic diff
    diff = OrderedDict()
    for k in sorted(current_policy.keys()):
        if candidate_policy[k] != current_policy[k]:
            diff[k] = {'from': current_policy[k], 'to': candidate_policy[k]}
    return ParticipantMetaUpdatePlan(
        candidate_policy=OrderedDict(sorted(candidate_policy.items())),
        promoted=promoted,
        reasons=reasons,
        diff=diff,
        metadata=metadata
    )

def write_json_artifact(obj, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2, sort_keys=True, ensure_ascii=False)

def emit_policy_artifacts(current_policy, candidate_policy, diff, base_path='.'):
    write_json_artifact(current_policy, f'{base_path}/brain_policy_participants.active.json')
    write_json_artifact(candidate_policy, f'{base_path}/brain_policy_participants.candidate.json')
    write_json_artifact(diff, f'{base_path}/brain_policy_participants.diff.json')
