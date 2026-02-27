import json
from copy import deepcopy
from pathlib import Path

import pytest

from engine.pattern_templates import PatternFamily
from engine.regime.regime_cluster_model import RegimeCluster
from engine.regime.regime_performance import build_regime_performance


def _decision(
    regime,
    template_id=None,
    eco_code=None,
    family=None,
    entry_model_id=None,
    action_type=None,
    news_window="none",
):
    payload = {"regime_cluster": regime, "news_window": news_window}
    if template_id is not None:
        payload.update(
            {"template_id": template_id, "eco_code": eco_code, "family": family}
        )
    if entry_model_id is not None:
        payload["entry_model_id"] = entry_model_id
    if action_type is not None:
        payload["action_type"] = action_type
    return payload


def _out(ev, r, mae=1.0, mfe=1.0, tit=5.0, dd=0.5):
    return {
        "ev": ev,
        "realized_R": r,
        "mae": mae,
        "mfe": mfe,
        "time_in_trade": tit,
        "drawdown": dd,
    }


# 1. Template/entry/action aggregation
def test_aggregate_template_performance_per_regime(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    decisions = [
        _decision(
            RegimeCluster.EXPANSIVE_TREND, "T1", "E1", PatternFamily.CONTINUATION
        ),
        _decision(
            RegimeCluster.EXPANSIVE_TREND, "T1", "E1", PatternFamily.CONTINUATION
        ),
        _decision(
            RegimeCluster.QUIET_ACCUMULATION, "T2", "E2", PatternFamily.LIQUIDITY
        ),
    ]
    outcomes = [_out(0.4, 1.0), _out(0.6, 1.0), _out(-0.1, -1.0)]

    artifacts = build_regime_performance(decisions, outcomes)
    keys = list(artifacts.template_stats.keys())
    assert keys == sorted(keys)

    key_t1 = [k for k in keys if "T1" in k][0]
    stat_t1 = artifacts.template_stats[key_t1]
    assert stat_t1.count == 2
    assert stat_t1.avg_ev == pytest.approx(0.5)
    assert stat_t1.winrate == pytest.approx(1.0)
    assert stat_t1.regime == RegimeCluster.EXPANSIVE_TREND

    key_t2 = [k for k in keys if "T2" in k][0]
    stat_t2 = artifacts.template_stats[key_t2]
    assert stat_t2.count == 1
    assert stat_t2.regime == RegimeCluster.QUIET_ACCUMULATION


def test_aggregate_entry_model_performance_per_regime(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    decisions = [
        _decision(RegimeCluster.CHOPPY_MANIPULATION, entry_model_id="E1"),
        _decision(RegimeCluster.CHOPPY_MANIPULATION, entry_model_id="E1"),
        _decision(RegimeCluster.CHOPPY_MANIPULATION, entry_model_id="E2"),
    ]
    outcomes = [_out(0.2, 1.0, tit=4), _out(-0.2, -1.0, tit=6), _out(0.1, 1.0, tit=5)]

    artifacts = build_regime_performance(decisions, outcomes)
    keys = list(artifacts.entry_stats.keys())
    assert keys == sorted(keys)

    stat_e1 = artifacts.entry_stats[keys[0]]
    assert stat_e1.count == 2
    assert stat_e1.avg_time_in_trade == pytest.approx(5.0)
    assert stat_e1.winrate == pytest.approx(0.5)

    stat_e2 = artifacts.entry_stats[keys[1]]
    assert stat_e2.count == 1
    assert stat_e2.winrate == pytest.approx(1.0)


def test_aggregate_action_type_performance_per_regime(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    decisions = [
        _decision(RegimeCluster.LIQUIDITY_DRAIN, action_type="OPEN_LONG"),
        _decision(RegimeCluster.LIQUIDITY_DRAIN, action_type="OPEN_LONG"),
        _decision(RegimeCluster.LIQUIDITY_DRAIN, action_type="OPEN_SHORT"),
    ]
    outcomes = [
        _out(0.3, 1.0, mae=0.4),
        _out(-0.1, -1.0, mae=0.6),
        _out(0.2, 1.0, mae=0.5),
    ]

    artifacts = build_regime_performance(decisions, outcomes)
    keys = list(artifacts.action_stats.keys())
    assert keys == sorted(keys)

    long_stat = artifacts.action_stats[keys[0]]
    assert long_stat.count == 2
    assert long_stat.avg_mae == pytest.approx(0.5)

    short_stat = artifacts.action_stats[keys[1]]
    assert short_stat.count == 1
    assert short_stat.avg_ev == pytest.approx(0.2)


# 2. News window bucketing
def test_news_window_bucketing_pre_during_post(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    decisions = [
        _decision(
            RegimeCluster.QUIET_ACCUMULATION,
            "T1",
            "E1",
            PatternFamily.LIQUIDITY,
            news_window="pre",
        ),
        _decision(
            RegimeCluster.QUIET_ACCUMULATION,
            "T1",
            "E1",
            PatternFamily.LIQUIDITY,
            news_window="during",
        ),
        _decision(
            RegimeCluster.QUIET_ACCUMULATION,
            "T1",
            "E1",
            PatternFamily.LIQUIDITY,
            news_window="post",
        ),
    ]
    outcomes = [_out(0.1, 1.0), _out(0.2, 1.0), _out(0.3, 1.0)]

    artifacts = build_regime_performance(decisions, outcomes)
    windows = {stat.news_window for stat in artifacts.template_stats.values()}
    assert windows == {"pre", "during", "post"}


# 3. Metrics correctness
def test_performance_metrics_ev_mae_mfe_variance_tailrisk(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    decisions = [
        _decision(
            RegimeCluster.EXPANSIVE_TREND, "T1", "E1", PatternFamily.CONTINUATION
        ),
        _decision(
            RegimeCluster.EXPANSIVE_TREND, "T1", "E1", PatternFamily.CONTINUATION
        ),
        _decision(
            RegimeCluster.EXPANSIVE_TREND, "T1", "E1", PatternFamily.CONTINUATION
        ),
    ]
    evs = [1.0, -0.5, 0.0]
    outcomes = [
        _out(evs[0], 1.0, mae=0.4, mfe=1.4, tit=4.0, dd=0.2),
        _out(evs[1], -1.0, mae=0.6, mfe=1.0, tit=6.0, dd=0.4),
        _out(evs[2], 1.0, mae=0.5, mfe=1.2, tit=5.0, dd=0.3),
    ]

    artifacts = build_regime_performance(decisions, outcomes)
    stat = next(iter(artifacts.template_stats.values()))

    assert stat.count == 3
    assert stat.avg_ev == pytest.approx(sum(evs) / 3)
    assert stat.winrate == pytest.approx(2 / 3)
    assert stat.avg_mae == pytest.approx((0.4 + 0.6 + 0.5) / 3)
    assert stat.avg_mfe == pytest.approx((1.4 + 1.0 + 1.2) / 3)
    assert stat.avg_drawdown == pytest.approx((0.2 + 0.4 + 0.3) / 3)
    assert stat.avg_time_in_trade == pytest.approx((4.0 + 6.0 + 5.0) / 3)

    # variance of EVs
    mean_ev = sum(evs) / 3
    variance = sum((ev - mean_ev) ** 2 for ev in evs) / 3
    assert stat.variance == pytest.approx(variance)

    # tail risk at 10th percentile -> lowest element for small sample
    assert stat.tail_risk == pytest.approx(-0.5)


# 4. Determinism
def test_performance_surfaces_deterministic(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    decisions = [
        _decision(
            RegimeCluster.QUIET_ACCUMULATION,
            "T1",
            "E1",
            PatternFamily.LIQUIDITY,
            entry_model_id="EM1",
            action_type="OPEN_LONG",
            news_window="pre",
        ),
        _decision(
            RegimeCluster.QUIET_ACCUMULATION,
            "T1",
            "E1",
            PatternFamily.LIQUIDITY,
            entry_model_id="EM1",
            action_type="OPEN_LONG",
            news_window="pre",
        ),
    ]
    outcomes = [_out(0.2, 1.0), _out(-0.2, -1.0)]

    first = build_regime_performance(decisions, outcomes)
    second = build_regime_performance(deepcopy(decisions), deepcopy(outcomes))

    assert first.template_stats == second.template_stats
    assert first.entry_stats == second.entry_stats
    assert first.action_stats == second.action_stats

    assert list(first.template_stats.keys()) == sorted(first.template_stats.keys())
    assert list(first.entry_stats.keys()) == sorted(first.entry_stats.keys())
    assert list(first.action_stats.keys()) == sorted(first.action_stats.keys())


# 5. Artifact validation
def test_performance_artifacts_written_correctly(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    decisions = [
        _decision(
            RegimeCluster.EXPANSIVE_TREND,
            "T1",
            "E1",
            PatternFamily.CONTINUATION,
            entry_model_id="EM1",
            action_type="OPEN_SHORT",
        ),
    ]
    outcomes = [_out(0.5, 1.0, dd=0.25)]

    artifacts = build_regime_performance(decisions, outcomes)

    base = Path("storage/reports/regime")
    tmpl_path = base / "regime_template_performance.json"
    entry_path = base / "regime_entry_performance.json"
    action_path = base / "regime_action_performance.json"

    for p in [tmpl_path, entry_path, action_path]:
        assert p.exists()
        data = json.loads(p.read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        # ensure schema-safe values (no enums)
        for value in data.values():
            assert not any(hasattr(v, "value") for v in value.values())

    # deterministic keys
    assert list(artifacts.template_stats.keys()) == sorted(
        artifacts.template_stats.keys()
    )
    assert list(artifacts.entry_stats.keys()) == sorted(artifacts.entry_stats.keys())
    assert list(artifacts.action_stats.keys()) == sorted(artifacts.action_stats.keys())


def test_missing_required_field_raises():
    decisions = [{"template_id": "T1"}]  # missing regime_cluster
    outcomes = [_out(0.1, 1.0)]
    with pytest.raises(ValueError):
        build_regime_performance(decisions, outcomes)


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        build_regime_performance([], [_out(0.1, 1.0)])
