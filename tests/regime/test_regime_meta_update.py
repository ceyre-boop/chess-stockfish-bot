import json
from copy import deepcopy
from pathlib import Path

from engine.pattern_templates import PatternFamily
from engine.regime.regime_cluster_model import RegimeCluster
from engine.regime.regime_drift import RegimeDriftSignal
from engine.regime.regime_meta_update import (
    MetaUpdateResult,
    RegimeMetaUpdatePlan,
    build_candidate_regime_policy,
    validate_and_promote_meta_policy,
)
from engine.regime.regime_performance import (
    RegimeEntryStats,
    RegimePerformanceArtifacts,
    RegimeTemplateStats,
)
from engine.regime.regime_policy_builder import synthesize_regime_policies

# Helpers


def _tmpl(regime, tid, ev, wr, dd, tail=0.1, count=60, family=PatternFamily.LIQUIDITY):
    return RegimeTemplateStats(
        regime=regime,
        template_id=tid,
        eco_code="E",
        family=family,
        count=count,
        avg_ev=ev,
        winrate=wr,
        avg_mae=0.5,
        avg_mfe=1.0,
        avg_time_in_trade=5.0,
        avg_drawdown=dd,
        variance=0.1,
        tail_risk=tail,
        news_window="none",
        metadata={"source": "synthetic"},
    )


def _entry(regime, eid, ev, wr, dd, tail=0.2, count=60):
    return RegimeEntryStats(
        regime=regime,
        entry_model_id=eid,
        count=count,
        avg_ev=ev,
        winrate=wr,
        avg_mae=0.5,
        avg_mfe=1.0,
        avg_time_in_trade=5.0,
        avg_drawdown=dd,
        variance=0.1,
        tail_risk=tail,
        news_window="none",
        metadata={"source": "synthetic"},
    )


def _perf(tmpls, entries):
    return RegimePerformanceArtifacts(
        template_stats={f"t_{i}": t for i, t in enumerate(tmpls)},
        entry_stats={f"e_{i}": e for i, e in enumerate(entries)},
        action_stats={},
        metadata={},
    )


def _drift(regime, entity_type, entity_id, severity, reason="drift"):
    return RegimeDriftSignal(
        regime=regime,
        entity_type=entity_type,
        entity_id=entity_id,
        severity=severity,
        reason=reason,
        metrics_before={},
        metrics_after={},
        metadata={},
    )


def test_candidate_policy_generation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    perf_current = _perf(
        [
            _tmpl(RegimeCluster.QUIET_ACCUMULATION, "T1", 0.3, 0.55, 1.0),
            _tmpl(RegimeCluster.QUIET_ACCUMULATION, "T2", 0.3, 0.55, 1.0),
        ],
        [],
    )
    current = synthesize_regime_policies(perf_current)

    perf_new = _perf(
        [
            _tmpl(RegimeCluster.QUIET_ACCUMULATION, "T1", 0.75, 0.7, 0.9),
            _tmpl(RegimeCluster.QUIET_ACCUMULATION, "T2", 0.25, 0.5, 1.1),
        ],
        [],
    )
    drift = [
        _drift(
            RegimeCluster.QUIET_ACCUMULATION,
            "template",
            "T2",
            "critical",
            reason="ev_crash",
        )
    ]

    plan = build_candidate_regime_policy(perf_new, current, drift)
    labels = {
        p.template_id: p.label
        for p in plan.candidate_policies.template_policies.values()
    }

    assert labels["T1"] == "PREFERRED"
    assert labels["T2"] == "DISCOURAGED"
    assert plan.metadata["regime_counts"][RegimeCluster.QUIET_ACCUMULATION.value] == 120


def test_meta_policy_requires_minimum_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    perf = _perf(
        [
            _tmpl(RegimeCluster.CHOPPY_MANIPULATION, "T1", 0.4, 0.55, 1.0, count=5),
        ],
        [],
    )
    current = synthesize_regime_policies(perf)
    plan = build_candidate_regime_policy(perf, current, [])

    result = validate_and_promote_meta_policy(plan, {"min_samples_per_regime": 20})

    assert result.promoted is False
    assert not result.metadata["validation"]["min_samples"][
        RegimeCluster.CHOPPY_MANIPULATION.value
    ]["ok"]


def test_meta_policy_no_flip_flops(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    perf_old = _perf(
        [
            _tmpl(RegimeCluster.EXPANSIVE_TREND, "T1", 0.3, 0.55, 1.0),
            _tmpl(RegimeCluster.EXPANSIVE_TREND, "T2", 0.3, 0.55, 1.0),
        ],
        [],
    )
    current = synthesize_regime_policies(perf_old)

    perf_new = _perf(
        [
            _tmpl(RegimeCluster.EXPANSIVE_TREND, "T1", 0.1, 0.4, 1.4),
            _tmpl(RegimeCluster.EXPANSIVE_TREND, "T2", 0.05, 0.35, 1.5),
        ],
        [],
    )
    drift = [
        _drift(RegimeCluster.EXPANSIVE_TREND, "template", "T1", "warning"),
        _drift(RegimeCluster.EXPANSIVE_TREND, "template", "T2", "warning"),
    ]
    plan = build_candidate_regime_policy(perf_new, current, drift)
    result = validate_and_promote_meta_policy(plan, {"max_label_change_rate": 0.5})

    assert result.promoted is False
    assert any(
        not v["ok"] for v in result.metadata["validation"]["label_change_rate"].values()
    )


def test_meta_policy_no_degradation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    perf = _perf(
        [
            _tmpl(RegimeCluster.LIQUIDITY_DRAIN, "T1", 0.6, 0.65, 0.8),
        ],
        [],
    )
    current = synthesize_regime_policies(perf)

    drift = [_drift(RegimeCluster.LIQUIDITY_DRAIN, "template", "T1", "warning")]
    plan = build_candidate_regime_policy(perf, current, drift)

    result = validate_and_promote_meta_policy(
        plan,
        {
            "min_samples_per_regime": 0,
            "max_label_change_rate": 1.0,
            "require_non_degradation": True,
        },
    )

    assert result.promoted is False
    assert result.metadata["validation"]["non_degradation"] is False


def test_meta_policy_monotonicity(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    perf = _perf(
        [
            _tmpl(RegimeCluster.QUIET_ACCUMULATION, "T1", 0.9, 0.7, 0.7),
        ],
        [],
    )
    current = synthesize_regime_policies(perf)

    improved = _perf(
        [
            _tmpl(RegimeCluster.QUIET_ACCUMULATION, "T1", 0.95, 0.72, 0.65),
        ],
        [],
    )

    plan = build_candidate_regime_policy(improved, current, [])
    # Force a monotonic violation by pretending current label is stricter
    key = next(iter(plan.current_policies.template_policies.keys()))
    strict_current = deepcopy(plan.current_policies)
    strict_current.template_policies[key] = strict_current.template_policies[
        key
    ].__class__(
        **{**strict_current.template_policies[key].__dict__, "label": "DISCOURAGED"}
    )
    plan = RegimeMetaUpdatePlan(
        current_policies=strict_current,
        candidate_policies=plan.candidate_policies,
        drift_signals=plan.drift_signals,
        validation_results=plan.validation_results,
        approved=plan.approved,
        reason=plan.reason,
        metadata=plan.metadata,
    )
    result = validate_and_promote_meta_policy(
        plan,
        {
            "min_samples_per_regime": 0,
            "max_label_change_rate": 1.0,
            "require_non_degradation": False,
        },
    )

    assert result.promoted is False  # monotonicity forbids upgrades
    assert result.metadata["validation"]["monotonic"] is False


def test_meta_policy_news_strictness(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    perf = _perf(
        [
            _tmpl(RegimeCluster.NEWS_SHOCK_EXPLOSION, "TN", 0.3, 0.55, 1.0, count=12),
        ],
        [],
    )
    current = synthesize_regime_policies(perf)
    drift = [_drift(RegimeCluster.NEWS_SHOCK_EXPLOSION, "template", "TN", "warning")]
    plan = build_candidate_regime_policy(perf, current, drift)

    result = validate_and_promote_meta_policy(
        plan,
        {
            "min_samples_per_regime": 10,
            "max_label_change_rate": 0.4,
            "require_non_degradation": False,
            "news_strict_factor": 2.0,
        },
    )

    assert result.promoted is False
    assert any(
        not v["ok"]
        for k, v in result.metadata["validation"]["min_samples"].items()
        if k == RegimeCluster.NEWS_SHOCK_EXPLOSION.value
    ) or any(
        not v["ok"]
        for k, v in result.metadata["validation"]["label_change_rate"].items()
        if k == RegimeCluster.NEWS_SHOCK_EXPLOSION.value
    )


def test_meta_policy_promotion_logic(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    perf = _perf(
        [
            _tmpl(RegimeCluster.LIQUIDITY_DRAIN, "TLD", 0.5, 0.6, 0.85, count=150),
        ],
        [],
    )
    current = synthesize_regime_policies(perf)
    plan = build_candidate_regime_policy(perf, current, [])

    result = validate_and_promote_meta_policy(
        plan,
        {
            "min_samples_per_regime": 10,
            "max_label_change_rate": 1.0,
            "require_non_degradation": False,
        },
    )

    assert result.promoted is True
    assert (
        result.active_policies.template_policies
        == plan.candidate_policies.template_policies
    )


def test_meta_policy_artifacts_written_correctly(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    perf = _perf(
        [
            _tmpl(RegimeCluster.QUIET_ACCUMULATION, "TA", 0.5, 0.62, 0.9, count=120),
        ],
        [],
    )
    current = synthesize_regime_policies(perf)
    plan = build_candidate_regime_policy(perf, current, [])

    result = validate_and_promote_meta_policy(
        plan,
        {
            "min_samples_per_regime": 0,
            "max_label_change_rate": 1.0,
            "require_non_degradation": False,
        },
    )

    base = Path("storage/policies/brain")
    active_path = base / "brain_policy_regime.active.json"
    cand_path = base / "brain_policy_regime.candidate.json"
    diff_path = base / "brain_policy_regime.diff.json"

    for p in [active_path, cand_path, diff_path]:
        assert p.exists()
        data = json.loads(p.read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        assert list(data.keys())

    diff = json.loads(diff_path.read_text(encoding="utf-8"))
    assert list(diff["template_policies"].keys()) == sorted(
        diff["template_policies"].keys()
    )

    # schema safety: no enums stored
    for payload in [active_path, cand_path]:
        parsed = json.loads(Path(payload).read_text(encoding="utf-8"))
        for section in ["template_policies", "entry_policies", "risk_profiles"]:
            for value in parsed.get(section, {}).values():
                assert not any(hasattr(v, "value") for v in value.values())


def test_meta_policy_deterministic(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    perf = _perf(
        [
            _tmpl(RegimeCluster.CHOPPY_MANIPULATION, "T0", 0.4, 0.6, 0.9, count=80),
            _tmpl(RegimeCluster.CHOPPY_MANIPULATION, "T1", 0.45, 0.62, 0.85, count=80),
        ],
        [],
    )
    current = synthesize_regime_policies(perf)
    drift = [
        _drift(RegimeCluster.CHOPPY_MANIPULATION, "template", "T0", "warning"),
    ]

    plan1 = build_candidate_regime_policy(perf, current, drift)
    plan2 = build_candidate_regime_policy(perf, current, drift)

    result1 = validate_and_promote_meta_policy(
        plan1,
        {
            "min_samples_per_regime": 0,
            "max_label_change_rate": 0.8,
            "require_non_degradation": False,
        },
    )
    result2 = validate_and_promote_meta_policy(
        plan2,
        {
            "min_samples_per_regime": 0,
            "max_label_change_rate": 0.8,
            "require_non_degradation": False,
        },
    )

    assert plan1 == plan2
    assert result1 == result2
    assert list(result1.diff["template_policies"].keys()) == sorted(
        result1.diff["template_policies"].keys()
    )
