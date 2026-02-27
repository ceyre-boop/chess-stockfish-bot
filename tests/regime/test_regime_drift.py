from engine.pattern_templates import PatternFamily
from engine.regime.regime_cluster_model import RegimeCluster
from engine.regime.regime_drift import compute_regime_drift
from engine.regime.regime_performance import (
    RegimeActionStats,
    RegimeEntryStats,
    RegimePerformanceArtifacts,
    RegimeTemplateStats,
)


def _tmpl(regime, tid, ev, wr, dd, tail=0.1, count=10):
    return RegimeTemplateStats(
        regime=regime,
        template_id=tid,
        eco_code="E",
        family=PatternFamily.LIQUIDITY,
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


def _entry(regime, eid, ev, wr, dd, tail=0.2, count=8):
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


def _action(regime, atype, ev, wr, dd, tail=0.2, count=6):
    return RegimeActionStats(
        regime=regime,
        action_type=atype,
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


def _artifacts(tmpls, entries, actions):
    return RegimePerformanceArtifacts(
        template_stats={f"t_{i}": t for i, t in enumerate(tmpls)},
        entry_stats={f"e_{i}": e for i, e in enumerate(entries)},
        action_stats={f"a_{i}": a for i, a in enumerate(actions)},
        metadata={},
    )


def test_template_degradation_detected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    before = _artifacts(
        [_tmpl(RegimeCluster.QUIET_ACCUMULATION, "T1", 0.65, 0.7, 0.7)],
        [],
        [],
    )
    after = _artifacts(
        [_tmpl(RegimeCluster.QUIET_ACCUMULATION, "T1", 0.05, 0.45, 1.5, tail=0.8)],
        [],
        [],
    )

    signals = compute_regime_drift(before, after)
    tpl = next(s for s in signals if s.entity_type == "template")
    assert tpl.entity_id == "T1"
    assert tpl.severity == "critical"
    assert "ev_drop" in tpl.reason


def test_entry_model_degradation_detected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    before = _artifacts(
        [],
        [_entry(RegimeCluster.EXPANSIVE_TREND, "E1", 0.5, 0.6, 0.6)],
        [],
    )
    after = _artifacts(
        [],
        [_entry(RegimeCluster.EXPANSIVE_TREND, "E1", 0.1, 0.4, 1.0)],
        [],
    )

    signals = compute_regime_drift(before, after)
    entry = next(s for s in signals if s.entity_type == "entry")
    assert entry.entity_id == "E1"
    assert entry.severity in {"warning", "critical"}
    assert "ev_drop" in entry.reason


def test_action_distribution_shift_detected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    before = _artifacts(
        [],
        [],
        [_action(RegimeCluster.LIQUIDITY_DRAIN, "OPEN_LONG", 0.6, 0.65, 0.7, count=12)],
    )
    after = _artifacts(
        [],
        [],
        [_action(RegimeCluster.LIQUIDITY_DRAIN, "OPEN_LONG", 0.2, 0.4, 1.0, count=4)],
    )

    signals = compute_regime_drift(before, after)
    act = next(s for s in signals if s.entity_type == "action")
    assert act.severity in {"warning", "critical"}
    assert "ev_drop" in act.reason


def test_risk_drift_detected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    before = _artifacts(
        [_tmpl(RegimeCluster.CHOPPY_MANIPULATION, "T2", 0.5, 0.55, 0.7, tail=0.2)],
        [],
        [],
    )
    after = _artifacts(
        [_tmpl(RegimeCluster.CHOPPY_MANIPULATION, "T2", 0.4, 0.5, 1.4, tail=0.9)],
        [],
        [],
    )

    signals = compute_regime_drift(before, after)
    risk = next(s for s in signals if s.entity_type == "risk")
    assert risk.entity_id == "T2"
    assert risk.severity in {"warning", "critical"}
    assert "risk_drift" in risk.reason


def test_news_shock_misalignment_detected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    before = _artifacts(
        [_tmpl(RegimeCluster.NEWS_SHOCK_EXPLOSION, "T3", 0.6, 0.6, 0.8, count=5)],
        [],
        [],
    )
    after = _artifacts(
        [_tmpl(RegimeCluster.NEWS_SHOCK_EXPLOSION, "T3", 0.5, 0.55, 0.85, count=15)],
        [],
        [],
    )

    signals = compute_regime_drift(before, after)
    assert any("too_aggressive_during_news_shock" == s.reason for s in signals)


def test_classifier_mismatch_detected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    before = _artifacts(
        [_tmpl(RegimeCluster.NEWS_POST_DIGESTION_TREND, "T4", 0.7, 0.7, 0.8)],
        [],
        [],
    )
    after = _artifacts(
        [_tmpl(RegimeCluster.NEWS_POST_DIGESTION_TREND, "T4", 0.5, 0.55, 0.9)],
        [],
        [],
    )

    signals = compute_regime_drift(before, after)
    assert any(s.reason == "too_passive_post_digest" for s in signals)


def test_no_drift_produces_no_signals(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    before = _artifacts(
        [_tmpl(RegimeCluster.QUIET_ACCUMULATION, "T1", 0.5, 0.6, 0.9)],
        [_entry(RegimeCluster.QUIET_ACCUMULATION, "E1", 0.4, 0.55, 0.8)],
        [_action(RegimeCluster.QUIET_ACCUMULATION, "OPEN_LONG", 0.3, 0.5, 0.7)],
    )
    after = _artifacts(
        [_tmpl(RegimeCluster.QUIET_ACCUMULATION, "T1", 0.5, 0.6, 0.9)],
        [_entry(RegimeCluster.QUIET_ACCUMULATION, "E1", 0.4, 0.55, 0.8)],
        [_action(RegimeCluster.QUIET_ACCUMULATION, "OPEN_LONG", 0.3, 0.5, 0.7)],
    )

    signals = compute_regime_drift(before, after)
    assert signals == []


def test_regime_drift_deterministic(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    before = _artifacts(
        [
            _tmpl(RegimeCluster.CHOPPY_MANIPULATION, "T0", 0.7, 0.7, 0.7),
            _tmpl(RegimeCluster.CHOPPY_MANIPULATION, "T1", 0.7, 0.7, 0.7),
        ],
        [_entry(RegimeCluster.CHOPPY_MANIPULATION, "E0", 0.6, 0.65, 0.7)],
        [_action(RegimeCluster.CHOPPY_MANIPULATION, "OPEN_LONG", 0.5, 0.55, 0.8)],
    )
    after = _artifacts(
        [
            _tmpl(RegimeCluster.CHOPPY_MANIPULATION, "T0", 0.3, 0.5, 1.1),
            _tmpl(RegimeCluster.CHOPPY_MANIPULATION, "T1", 0.4, 0.55, 1.0),
        ],
        [_entry(RegimeCluster.CHOPPY_MANIPULATION, "E0", 0.2, 0.45, 1.2)],
        [_action(RegimeCluster.CHOPPY_MANIPULATION, "OPEN_LONG", 0.1, 0.35, 1.1)],
    )

    first = compute_regime_drift(before, after)
    second = compute_regime_drift(before, after)

    def _severity_rank(s):
        return {"critical": 0, "warning": 1, "info": 2}.get(s.severity, 3)

    expected_order = sorted(
        first,
        key=lambda s: (s.regime.value, s.entity_type, s.entity_id, _severity_rank(s)),
    )

    assert first == second
    assert [
        (s.regime.value, s.entity_type, s.entity_id, s.severity) for s in first
    ] == [
        (s.regime.value, s.entity_type, s.entity_id, s.severity) for s in expected_order
    ]
