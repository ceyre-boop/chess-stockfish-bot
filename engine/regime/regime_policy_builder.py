from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable

from engine.pattern_templates import PatternFamily
from engine.regime.regime_cluster_model import RegimeCluster
from engine.regime.regime_performance import (
    RegimeEntryStats,
    RegimePerformanceArtifacts,
    RegimeTemplateStats,
)


@dataclass(frozen=True)
class RegimeTemplatePolicy:
    regime: RegimeCluster
    template_id: str
    eco_code: str
    label: str  # "PREFERRED", "ALLOWED", "DISCOURAGED", "DISABLED"
    reason: str
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class RegimeEntryPolicy:
    regime: RegimeCluster
    entry_model_id: str
    label: str
    reason: str
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class RegimeRiskProfile:
    regime: RegimeCluster
    max_per_trade_R: float
    max_concurrent_R: float
    max_daily_R: float
    allowed_action_types: Iterable[str]
    allowed_template_families: Iterable[PatternFamily]
    news_overrides: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class RegimePolicyArtifacts:
    template_policies: Dict[str, RegimeTemplatePolicy]
    entry_policies: Dict[str, RegimeEntryPolicy]
    risk_profiles: Dict[str, RegimeRiskProfile]
    metadata: Dict[str, Any]


def _label_from_stats(stat: RegimeTemplateStats | RegimeEntryStats) -> str:
    # Deterministic, simple thresholds.
    if stat.avg_ev >= 0.5 and stat.winrate >= 0.6 and stat.avg_drawdown <= 1.0:
        return "PREFERRED"
    if stat.avg_ev <= -0.2 or stat.winrate < 0.4 or stat.avg_drawdown > 1.5:
        return "DISCOURAGED"
    return "ALLOWED"


def _reason_from_stats(stat: RegimeTemplateStats | RegimeEntryStats, label: str) -> str:
    return f"label={label}; ev={stat.avg_ev:.2f}; winrate={stat.winrate:.2f}; dd={stat.avg_drawdown:.2f}"


def _serialize(obj: Any) -> Dict[str, Any]:
    data = asdict(obj)
    for key, val in list(data.items()):
        if isinstance(val, (RegimeCluster, PatternFamily)):
            data[key] = val.value
        elif isinstance(val, list):
            data[key] = [v.value if isinstance(v, PatternFamily) else v for v in val]
    return data


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _risk_profile_for_regime(regime: RegimeCluster) -> RegimeRiskProfile:
    base = {
        "max_per_trade_R": 1.0,
        "max_concurrent_R": 3.0,
        "max_daily_R": 5.0,
        "allowed_action_types": ["OPEN_LONG", "OPEN_SHORT", "MANAGE_POSITION"],
        "allowed_template_families": list(PatternFamily),
        "news_overrides": {},
    }

    if regime == RegimeCluster.NEWS_SHOCK_EXPLOSION:
        base.update(
            {
                "max_per_trade_R": 0.0,
                "max_concurrent_R": 0.0,
                "max_daily_R": 0.0,
                "allowed_action_types": ["NO_TRADE"],
                "allowed_template_families": [],
                "news_overrides": {"block_fresh_entry": True},
            }
        )
    elif regime == RegimeCluster.NEWS_PRE_RELEASE_COMPRESSION:
        base.update(
            {
                "max_per_trade_R": 0.25,
                "max_concurrent_R": 1.0,
                "max_daily_R": 1.5,
                "allowed_action_types": ["OPEN_LONG", "OPEN_SHORT"],
                "allowed_template_families": [
                    PatternFamily.LIQUIDITY,
                    PatternFamily.MEAN_REVERSION,
                ],
                "news_overrides": {"restrict_continuation": True},
            }
        )
    elif regime == RegimeCluster.NEWS_POST_DIGESTION_TREND:
        base.update(
            {
                "max_per_trade_R": 0.75,
                "max_concurrent_R": 2.0,
                "max_daily_R": 3.0,
                "allowed_template_families": [
                    PatternFamily.LIQUIDITY,
                    PatternFamily.CONTINUATION,
                ],
                "news_overrides": {"boost_liquidity": True},
            }
        )
    elif regime in {
        RegimeCluster.VOLATILITY_BREAKOUT,
        RegimeCluster.CHOPPY_MANIPULATION,
    }:
        base.update(
            {"max_per_trade_R": 0.6, "max_concurrent_R": 2.0, "max_daily_R": 2.5}
        )
    elif regime == RegimeCluster.LIQUIDITY_DRAIN:
        base.update(
            {"max_per_trade_R": 0.5, "max_concurrent_R": 1.5, "max_daily_R": 2.0}
        )

    return RegimeRiskProfile(
        regime=regime,
        max_per_trade_R=base["max_per_trade_R"],
        max_concurrent_R=base["max_concurrent_R"],
        max_daily_R=base["max_daily_R"],
        allowed_action_types=list(base["allowed_action_types"]),
        allowed_template_families=list(base["allowed_template_families"]),
        news_overrides=base["news_overrides"],
        metadata={},
    )


def synthesize_regime_policies(
    perf: RegimePerformanceArtifacts,
) -> RegimePolicyArtifacts:
    template_policies: Dict[str, RegimeTemplatePolicy] = {}
    entry_policies: Dict[str, RegimeEntryPolicy] = {}
    risk_profiles: Dict[str, RegimeRiskProfile] = {}

    regimes_seen = set()
    tmpl_stats_sorted = sorted(
        perf.template_stats.values(),
        key=lambda s: (s.regime.value, s.template_id, s.eco_code),
    )
    for stat in tmpl_stats_sorted:
        regimes_seen.add(stat.regime)
        label = _label_from_stats(stat)
        reason = _reason_from_stats(stat, label)
        policy_key = f"{stat.regime.value}|{stat.template_id}|{stat.eco_code}"
        template_policies[policy_key] = RegimeTemplatePolicy(
            regime=stat.regime,
            template_id=stat.template_id,
            eco_code=stat.eco_code,
            label=label,
            reason=reason,
            metadata={"news_window": stat.news_window},
        )

    entry_stats_sorted = sorted(
        perf.entry_stats.values(),
        key=lambda s: (s.regime.value, s.entry_model_id, s.news_window),
    )
    for stat in entry_stats_sorted:
        regimes_seen.add(stat.regime)
        label = _label_from_stats(stat)
        reason = _reason_from_stats(stat, label)
        policy_key = f"{stat.regime.value}|{stat.entry_model_id}|{stat.news_window}"
        entry_policies[policy_key] = RegimeEntryPolicy(
            regime=stat.regime,
            entry_model_id=stat.entry_model_id,
            label=label,
            reason=reason,
            metadata={"news_window": stat.news_window},
        )

    if not regimes_seen:
        placeholder_regime = RegimeCluster.QUIET_ACCUMULATION
        placeholder_key_t = f"{placeholder_regime.value}|__placeholder_template__"
        template_policies[placeholder_key_t] = RegimeTemplatePolicy(
            regime=placeholder_regime,
            template_id="__placeholder__",
            eco_code="__placeholder__",
            label="ALLOWED",
            reason="placeholder",
            metadata={"news_window": "none"},
        )
        placeholder_key_e = f"{placeholder_regime.value}|__placeholder_entry__"
        entry_policies[placeholder_key_e] = RegimeEntryPolicy(
            regime=placeholder_regime,
            entry_model_id="__placeholder__",
            label="ALLOWED",
            reason="placeholder",
            metadata={"news_window": "none"},
        )
        return RegimePolicyArtifacts(
            template_policies=template_policies,
            entry_policies=entry_policies,
            risk_profiles=risk_profiles,
            metadata={"regimes": []},
        )

    # Ensure no empty sets per regime encountered
    for regime in sorted(regimes_seen, key=lambda r: r.value):
        risk_profiles[regime.value] = _risk_profile_for_regime(regime)
        has_template = any(p.regime == regime for p in template_policies.values())
        if not has_template:
            policy_key = f"{regime.value}|__placeholder_template__"
            template_policies[policy_key] = RegimeTemplatePolicy(
                regime=regime,
                template_id="__placeholder__",
                eco_code="__placeholder__",
                label="ALLOWED",
                reason="placeholder",
                metadata={"news_window": "none"},
            )
        has_entry = any(p.regime == regime for p in entry_policies.values())
        if not has_entry:
            policy_key = f"{regime.value}|__placeholder_entry__"
            entry_policies[policy_key] = RegimeEntryPolicy(
                regime=regime,
                entry_model_id="__placeholder__",
                label="ALLOWED",
                reason="placeholder",
                metadata={"news_window": "none"},
            )

    artifacts = RegimePolicyArtifacts(
        template_policies=template_policies,
        entry_policies=entry_policies,
        risk_profiles=risk_profiles,
        metadata={"regimes": sorted(r.value for r in regimes_seen)},
    )

    storage_root = Path("storage/policies/brain")
    tmpl_payload = {k: _serialize(v) for k, v in template_policies.items()}
    entry_payload = {k: _serialize(v) for k, v in entry_policies.items()}
    risk_payload = {k: _serialize(v) for k, v in risk_profiles.items()}

    _write_json(storage_root / "brain_policy_templates.by_regime.json", tmpl_payload)
    _write_json(storage_root / "brain_policy_entries.by_regime.json", entry_payload)
    _write_json(storage_root / "regime_risk_profile.json", risk_payload)

    return artifacts
