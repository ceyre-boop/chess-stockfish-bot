from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from engine.pattern_templates import PatternFamily
from engine.regime.regime_cluster_model import RegimeCluster
from engine.regime.regime_drift import RegimeDriftSignal
from engine.regime.regime_performance import RegimePerformanceArtifacts
from engine.regime.regime_policy_builder import (
    RegimeEntryPolicy,
    RegimePolicyArtifacts,
    RegimeRiskProfile,
    RegimeTemplatePolicy,
    synthesize_regime_policies,
)

_LABEL_ORDER = ["PREFERRED", "ALLOWED", "DISCOURAGED", "DISABLED"]


@dataclass(frozen=True)
class RegimeMetaUpdatePlan:
    current_policies: RegimePolicyArtifacts
    candidate_policies: RegimePolicyArtifacts
    drift_signals: List[RegimeDriftSignal]
    validation_results: Dict[str, Any]
    approved: bool
    reason: str
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class MetaUpdateResult:
    promoted: bool
    active_policies: RegimePolicyArtifacts
    candidate_policies: RegimePolicyArtifacts
    diff: Dict[str, Any]
    metadata: Dict[str, Any]


def _label_index(label: str) -> int:
    return _LABEL_ORDER.index(label) if label in _LABEL_ORDER else len(_LABEL_ORDER)


def _downgrade_label(label: str, severity: str) -> str:
    step = 0
    if severity == "critical":
        step = 2 if label == "PREFERRED" else 1
    elif severity == "warning":
        step = 1
    idx = min(len(_LABEL_ORDER) - 1, _label_index(label) + step)
    return _LABEL_ORDER[idx]


def _serialize_policy(obj: Any) -> Dict[str, Any]:
    data = asdict(obj)
    for key, val in list(data.items()):
        if isinstance(val, RegimeCluster):
            data[key] = val.value
        elif isinstance(val, list):
            normalized = []
            for v in val:
                if isinstance(v, RegimeCluster):
                    normalized.append(v.value)
                elif isinstance(v, PatternFamily):
                    normalized.append(v.value)
                else:
                    normalized.append(v)
            data[key] = normalized
    return data


def _serialize_artifacts(artifacts: RegimePolicyArtifacts) -> Dict[str, Any]:
    return {
        "template_policies": {
            k: _serialize_policy(v) for k, v in artifacts.template_policies.items()
        },
        "entry_policies": {
            k: _serialize_policy(v) for k, v in artifacts.entry_policies.items()
        },
        "risk_profiles": {
            k: _serialize_policy(v) for k, v in artifacts.risk_profiles.items()
        },
        "metadata": artifacts.metadata,
    }


def _tighten_risk(profile: RegimeRiskProfile, severity: str) -> RegimeRiskProfile:
    factor = 1.0
    if severity == "critical":
        factor = 0.5
    elif severity == "warning":
        factor = 0.8
    return replace(
        profile,
        max_per_trade_R=round(profile.max_per_trade_R * factor, 3),
        max_concurrent_R=round(profile.max_concurrent_R * factor, 3),
        max_daily_R=round(profile.max_daily_R * factor, 3),
        metadata={**profile.metadata, "tightened": True, "severity": severity},
    )


def _regime_counts(perf: RegimePerformanceArtifacts) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for stat in perf.template_stats.values():
        counts[stat.regime.value] = counts.get(stat.regime.value, 0) + stat.count
    for stat in perf.entry_stats.values():
        counts[stat.regime.value] = counts.get(stat.regime.value, 0) + stat.count
    return counts


def build_candidate_regime_policy(
    perf: RegimePerformanceArtifacts,
    current_policies: RegimePolicyArtifacts,
    drift_signals: List[RegimeDriftSignal],
) -> RegimeMetaUpdatePlan:
    base = synthesize_regime_policies(perf)

    tmpl_policies: Dict[str, RegimeTemplatePolicy] = dict(base.template_policies)
    entry_policies: Dict[str, RegimeEntryPolicy] = dict(base.entry_policies)
    risk_profiles: Dict[str, RegimeRiskProfile] = dict(base.risk_profiles)

    # Apply drift-aware downgrades
    for signal in sorted(
        drift_signals,
        key=lambda s: (s.regime.value, s.entity_type, s.entity_id, s.severity),
    ):
        if signal.entity_type == "template":
            for key, pol in list(tmpl_policies.items()):
                if pol.regime == signal.regime and pol.template_id == signal.entity_id:
                    new_label = _downgrade_label(pol.label, signal.severity)
                    tmpl_policies[key] = replace(
                        pol,
                        label=new_label,
                        reason=f"drift={signal.reason}; prev={pol.label}",
                    )
        elif signal.entity_type == "entry":
            for key, pol in list(entry_policies.items()):
                if (
                    pol.regime == signal.regime
                    and pol.entry_model_id == signal.entity_id
                ):
                    new_label = _downgrade_label(pol.label, signal.severity)
                    entry_policies[key] = replace(
                        pol,
                        label=new_label,
                        reason=f"drift={signal.reason}; prev={pol.label}",
                    )
        elif signal.entity_type == "risk":
            regime_key = signal.regime.value
            if regime_key in risk_profiles:
                risk_profiles[regime_key] = _tighten_risk(
                    risk_profiles[regime_key], signal.severity
                )

    candidate = RegimePolicyArtifacts(
        template_policies=tmpl_policies,
        entry_policies=entry_policies,
        risk_profiles=risk_profiles,
        metadata={"regimes": base.metadata.get("regimes", [])},
    )

    plan_metadata = {"regime_counts": _regime_counts(perf)}
    return RegimeMetaUpdatePlan(
        current_policies=current_policies,
        candidate_policies=candidate,
        drift_signals=drift_signals,
        validation_results={},
        approved=False,
        reason="",
        metadata=plan_metadata,
    )


def _labels_by_regime(
    policies: Iterable[Tuple[str, Any]], attr: str
) -> Dict[str, Dict[str, str]]:
    by_regime: Dict[str, Dict[str, str]] = {}
    for key, pol in policies:
        reg = getattr(pol, "regime")
        regime_val = reg.value if isinstance(reg, RegimeCluster) else str(reg)
        by_regime.setdefault(regime_val, {})[key] = getattr(pol, attr)
    return by_regime


def _compute_label_change_rate(
    current: RegimePolicyArtifacts, candidate: RegimePolicyArtifacts
) -> Dict[str, float]:
    tmpl_curr = _labels_by_regime(current.template_policies.items(), "label")
    tmpl_cand = _labels_by_regime(candidate.template_policies.items(), "label")
    entry_curr = _labels_by_regime(current.entry_policies.items(), "label")
    entry_cand = _labels_by_regime(candidate.entry_policies.items(), "label")

    regimes = (
        set(tmpl_curr.keys())
        | set(tmpl_cand.keys())
        | set(entry_curr.keys())
        | set(entry_cand.keys())
    )
    rates: Dict[str, float] = {}
    for regime in sorted(regimes):
        changed = 0
        total = 0
        for key in set(tmpl_curr.get(regime, {})) | set(tmpl_cand.get(regime, {})):
            total += 1
            if tmpl_curr.get(regime, {}).get(key) != tmpl_cand.get(regime, {}).get(key):
                changed += 1
        for key in set(entry_curr.get(regime, {})) | set(entry_cand.get(regime, {})):
            total += 1
            if entry_curr.get(regime, {}).get(key) != entry_cand.get(regime, {}).get(
                key
            ):
                changed += 1
        rates[regime] = (changed / total) if total else 0.0
    return rates


def _is_news_regime(regime_value: str) -> bool:
    return regime_value in {
        RegimeCluster.NEWS_SHOCK_EXPLOSION.value,
        RegimeCluster.NEWS_PRE_RELEASE_COMPRESSION.value,
        RegimeCluster.NEWS_POST_DIGESTION_TREND.value,
    }


def _non_degradation_ok(plan: RegimeMetaUpdatePlan, require: bool) -> bool:
    if not require:
        return True
    return not any(
        s.severity in {"warning", "critical"} and s.entity_type in {"template", "entry"}
        for s in plan.drift_signals
    )


def _monotonic_ok(
    current: RegimePolicyArtifacts, candidate: RegimePolicyArtifacts
) -> bool:
    for key, cand in candidate.template_policies.items():
        curr = current.template_policies.get(key)
        if curr and _label_index(cand.label) < _label_index(curr.label):
            return False
    for key, cand in candidate.entry_policies.items():
        curr = current.entry_policies.get(key)
        if curr and _label_index(cand.label) < _label_index(curr.label):
            return False
    return True


def _diff_policies(
    current: RegimePolicyArtifacts, candidate: RegimePolicyArtifacts
) -> Dict[str, Any]:
    tmpl_diff: Dict[str, Any] = {}
    for key in sorted(
        set(current.template_policies) | set(candidate.template_policies)
    ):
        curr = current.template_policies.get(key)
        cand = candidate.template_policies.get(key)
        if not curr or not cand:
            tmpl_diff[key] = {
                "from": _serialize_policy(curr) if curr else None,
                "to": _serialize_policy(cand) if cand else None,
            }
        elif curr.label != cand.label or curr.reason != cand.reason:
            tmpl_diff[key] = {
                "from": _serialize_policy(curr),
                "to": _serialize_policy(cand),
            }

    entry_diff: Dict[str, Any] = {}
    for key in sorted(set(current.entry_policies) | set(candidate.entry_policies)):
        curr = current.entry_policies.get(key)
        cand = candidate.entry_policies.get(key)
        if not curr or not cand:
            entry_diff[key] = {
                "from": _serialize_policy(curr) if curr else None,
                "to": _serialize_policy(cand) if cand else None,
            }
        elif curr.label != cand.label or curr.reason != cand.reason:
            entry_diff[key] = {
                "from": _serialize_policy(curr),
                "to": _serialize_policy(cand),
            }

    risk_diff: Dict[str, Any] = {}
    for key in sorted(set(current.risk_profiles) | set(candidate.risk_profiles)):
        curr = current.risk_profiles.get(key)
        cand = candidate.risk_profiles.get(key)
        if not curr or not cand:
            risk_diff[key] = {
                "from": _serialize_policy(curr) if curr else None,
                "to": _serialize_policy(cand) if cand else None,
            }
        else:
            curr_dict = _serialize_policy(curr)
            cand_dict = _serialize_policy(cand)
            if curr_dict != cand_dict:
                risk_diff[key] = {"from": curr_dict, "to": cand_dict}

    return {
        "template_policies": tmpl_diff,
        "entry_policies": entry_diff,
        "risk_profiles": risk_diff,
    }


def _write_payload(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def validate_and_promote_meta_policy(
    plan: RegimeMetaUpdatePlan, constraints: Dict[str, Any]
) -> MetaUpdateResult:
    min_samples = constraints.get("min_samples_per_regime", 0)
    max_change = constraints.get("max_label_change_rate", 1.0)
    require_non_degradation = constraints.get("require_non_degradation", False)
    news_strict_factor = constraints.get("news_strict_factor", 1.0)

    validation: Dict[str, Any] = {}
    counts = plan.metadata.get("regime_counts", {})

    # Minimum samples
    min_samples_ok = True
    min_report: Dict[str, Any] = {}
    for regime, count in counts.items():
        needed = min_samples * (news_strict_factor if _is_news_regime(regime) else 1.0)
        ok = count >= needed
        min_report[regime] = {"count": count, "required": needed, "ok": ok}
        if not ok:
            min_samples_ok = False
    validation["min_samples"] = min_report

    # Label change rate
    change_rates = _compute_label_change_rate(
        plan.current_policies, plan.candidate_policies
    )
    rate_ok = True
    rate_report: Dict[str, Any] = {}
    for regime, rate in change_rates.items():
        limit = max_change / (news_strict_factor if _is_news_regime(regime) else 1.0)
        ok = rate <= limit
        rate_report[regime] = {"rate": rate, "limit": limit, "ok": ok}
        if not ok:
            rate_ok = False
    validation["label_change_rate"] = rate_report

    # Non-degradation
    non_deg_ok = _non_degradation_ok(plan, require_non_degradation)
    validation["non_degradation"] = non_deg_ok

    # Monotonicity
    monotonic_ok = _monotonic_ok(plan.current_policies, plan.candidate_policies)
    validation["monotonic"] = monotonic_ok

    all_ok = min_samples_ok and rate_ok and non_deg_ok and monotonic_ok

    diff = _diff_policies(plan.current_policies, plan.candidate_policies)

    promoted = all_ok
    active = plan.candidate_policies if promoted else plan.current_policies

    storage_root = Path("storage/policies/brain")
    _write_payload(
        storage_root / "brain_policy_regime.active.json", _serialize_artifacts(active)
    )
    _write_payload(
        storage_root / "brain_policy_regime.candidate.json",
        _serialize_artifacts(plan.candidate_policies),
    )
    _write_payload(storage_root / "brain_policy_regime.diff.json", diff)

    return MetaUpdateResult(
        promoted=promoted,
        active_policies=active,
        candidate_policies=plan.candidate_policies,
        diff=diff,
        metadata={"validation": validation},
    )
