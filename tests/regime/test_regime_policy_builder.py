import json
from pathlib import Path

from engine.pattern_templates import PatternFamily
from engine.regime.regime_cluster_model import RegimeCluster
from engine.regime.regime_performance import (
    RegimeEntryStats,
    RegimePerformanceArtifacts,
    RegimeTemplateStats,
)
from engine.regime.regime_policy_builder import synthesize_regime_policies

# Helpers


def _tmpl(regime, tid, eco, fam, ev, wr, dd, news_window="none"):
    return RegimeTemplateStats(
        regime=regime,
        template_id=tid,
        eco_code=eco,
        family=fam,
        count=20,
        avg_ev=ev,
        winrate=wr,
        avg_mae=0.5,
        avg_mfe=1.0,
        avg_time_in_trade=5.0,
        avg_drawdown=dd,
        variance=0.1,
        tail_risk=0.2,
        news_window=news_window,
        metadata={},
    )


def _entry(regime, eid, ev, wr, dd, news_window="none"):
    return RegimeEntryStats(
        regime=regime,
        entry_model_id=eid,
        count=15,
        avg_ev=ev,
        winrate=wr,
        avg_mae=0.5,
        avg_mfe=1.0,
        avg_time_in_trade=5.0,
        avg_drawdown=dd,
        variance=0.1,
        tail_risk=0.2,
        news_window=news_window,
        metadata={},
    )


def _artifacts(tmpls, entries):
    return RegimePerformanceArtifacts(
        template_stats={f"t_{i}": t for i, t in enumerate(tmpls)},
        entry_stats={f"e_{i}": e for i, e in enumerate(entries)},
        action_stats={},
        metadata={},
    )


# 1. Template & entry policy synthesis


def test_template_policy_synthesis_per_regime(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    perf = _artifacts(
        [
            _tmpl(
                RegimeCluster.EXPANSIVE_TREND,
                "T_PREF",
                "E1",
                PatternFamily.CONTINUATION,
                0.6,
                0.65,
                0.8,
            ),
            _tmpl(
                RegimeCluster.EXPANSIVE_TREND,
                "T_ALLOW",
                "E2",
                PatternFamily.LIQUIDITY,
                0.2,
                0.55,
                1.1,
            ),
            _tmpl(
                RegimeCluster.EXPANSIVE_TREND,
                "T_DISC",
                "E3",
                PatternFamily.CONTINUATION,
                -0.3,
                0.35,
                1.6,
            ),
        ],
        [],
    )
    artifacts = synthesize_regime_policies(perf)
    labels = {p.template_id: p.label for p in artifacts.template_policies.values()}
    assert labels["T_PREF"] == "PREFERRED"
    assert labels["T_ALLOW"] == "ALLOWED"
    assert labels["T_DISC"] == "DISCOURAGED"


def test_entry_policy_synthesis_per_regime(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    perf = _artifacts(
        [],
        [
            _entry(RegimeCluster.CHOPPY_MANIPULATION, "E_PREF", 0.55, 0.65, 0.9),
            _entry(RegimeCluster.CHOPPY_MANIPULATION, "E_ALLOW", 0.2, 0.52, 1.1),
            _entry(RegimeCluster.CHOPPY_MANIPULATION, "E_DISC", -0.25, 0.35, 1.7),
        ],
    )
    artifacts = synthesize_regime_policies(perf)
    labels = {p.entry_model_id: p.label for p in artifacts.entry_policies.values()}
    assert labels["E_PREF"] == "PREFERRED"
    assert labels["E_ALLOW"] == "ALLOWED"
    assert labels["E_DISC"] == "DISCOURAGED"


# 2. News-aware overrides


def test_news_shock_forces_no_trade(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    perf = _artifacts(
        [
            _tmpl(
                RegimeCluster.NEWS_SHOCK_EXPLOSION,
                "T_NEWS",
                "E",
                PatternFamily.LIQUIDITY,
                0.8,
                0.7,
                0.9,
                news_window="during",
            )
        ],
        [],
    )
    artifacts = synthesize_regime_policies(perf)
    risk = artifacts.risk_profiles[RegimeCluster.NEWS_SHOCK_EXPLOSION.value]
    assert risk.max_per_trade_R == 0.0
    assert risk.allowed_action_types == ["NO_TRADE"]
    assert risk.allowed_template_families == []


def test_pre_release_restricts_continuation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    perf = _artifacts(
        [
            _tmpl(
                RegimeCluster.NEWS_PRE_RELEASE_COMPRESSION,
                "T_PRE",
                "E",
                PatternFamily.CONTINUATION,
                0.7,
                0.7,
                0.8,
                news_window="pre",
            )
        ],
        [],
    )
    artifacts = synthesize_regime_policies(perf)
    risk = artifacts.risk_profiles[RegimeCluster.NEWS_PRE_RELEASE_COMPRESSION.value]
    assert risk.max_per_trade_R <= 0.25
    assert set(risk.allowed_template_families) == {
        PatternFamily.LIQUIDITY,
        PatternFamily.MEAN_REVERSION,
    }


def test_post_digest_cautious_continuation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    perf = _artifacts(
        [
            _tmpl(
                RegimeCluster.NEWS_POST_DIGESTION_TREND,
                "T_POST",
                "E",
                PatternFamily.CONTINUATION,
                0.6,
                0.65,
                0.9,
                news_window="post",
            )
        ],
        [],
    )
    artifacts = synthesize_regime_policies(perf)
    risk = artifacts.risk_profiles[RegimeCluster.NEWS_POST_DIGESTION_TREND.value]
    assert PatternFamily.CONTINUATION in risk.allowed_template_families
    assert risk.max_per_trade_R <= 0.75


# 3. Policy monotonicity


def test_policy_label_monotonicity_rules(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    perf = _artifacts(
        [
            _tmpl(
                RegimeCluster.VOLATILITY_BREAKOUT,
                "T_HIGH",
                "E1",
                PatternFamily.CONTINUATION,
                0.7,
                0.7,
                0.9,
            ),
            _tmpl(
                RegimeCluster.VOLATILITY_BREAKOUT,
                "T_LOW",
                "E2",
                PatternFamily.CONTINUATION,
                -0.4,
                0.3,
                1.8,
            ),
        ],
        [
            _entry(RegimeCluster.VOLATILITY_BREAKOUT, "E_HIGH", 0.6, 0.65, 0.9),
            _entry(RegimeCluster.VOLATILITY_BREAKOUT, "E_LOW", -0.3, 0.35, 1.6),
        ],
    )
    artifacts = synthesize_regime_policies(perf)
    labels_t = {p.template_id: p.label for p in artifacts.template_policies.values()}
    labels_e = {p.entry_model_id: p.label for p in artifacts.entry_policies.values()}
    assert _label_rank(labels_t["T_HIGH"]) <= _label_rank(labels_t["T_LOW"])
    assert _label_rank(labels_e["E_HIGH"]) <= _label_rank(labels_e["E_LOW"])


def _label_rank(label: str) -> int:
    order = ["PREFERRED", "ALLOWED", "DISCOURAGED", "DISABLED"]
    return order.index(label)


# 4. Determinism


def test_policy_generation_deterministic(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    perf = _artifacts(
        [
            _tmpl(
                RegimeCluster.CHOPPY_MANIPULATION,
                "T1",
                "E1",
                PatternFamily.LIQUIDITY,
                0.4,
                0.55,
                1.0,
            ),
            _tmpl(
                RegimeCluster.CHOPPY_MANIPULATION,
                "T2",
                "E2",
                PatternFamily.CONTINUATION,
                0.3,
                0.52,
                1.1,
            ),
        ],
        [_entry(RegimeCluster.CHOPPY_MANIPULATION, "E1", 0.25, 0.5, 1.0)],
    )
    first = synthesize_regime_policies(perf)
    second = synthesize_regime_policies(perf)

    assert first.template_policies == second.template_policies
    assert first.entry_policies == second.entry_policies
    assert first.risk_profiles == second.risk_profiles
    assert list(first.template_policies.keys()) == sorted(
        first.template_policies.keys()
    )
    assert list(first.entry_policies.keys()) == sorted(first.entry_policies.keys())


# 5. Artifact validation


def test_policy_artifacts_written_correctly(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    perf = _artifacts(
        [
            _tmpl(
                RegimeCluster.QUIET_ACCUMULATION,
                "T_ART",
                "E",
                PatternFamily.LIQUIDITY,
                0.5,
                0.62,
                0.9,
            )
        ],
        [_entry(RegimeCluster.QUIET_ACCUMULATION, "E_ART", 0.4, 0.55, 1.0)],
    )
    artifacts = synthesize_regime_policies(perf)

    base = Path("storage/policies/brain")
    tmpl_path = base / "brain_policy_templates.by_regime.json"
    entry_path = base / "brain_policy_entries.by_regime.json"
    risk_path = base / "regime_risk_profile.json"

    for p in [tmpl_path, entry_path, risk_path]:
        assert p.exists()
        data = json.loads(p.read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        # schema-safe: no enums
        for value in data.values():
            assert not any(hasattr(v, "value") for v in value.values())

    # global cap sanity (no profile exceeds daily cap of 5.0 defined in builder base)
    for profile in artifacts.risk_profiles.values():
        assert profile.max_daily_R <= 5.0

    # deterministic keys
    assert list(artifacts.template_policies.keys()) == sorted(
        artifacts.template_policies.keys()
    )
    assert list(artifacts.entry_policies.keys()) == sorted(
        artifacts.entry_policies.keys()
    )
