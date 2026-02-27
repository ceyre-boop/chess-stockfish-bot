from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List

from engine.regime.regime_cluster_model import RegimeCluster
from engine.regime.regime_performance import (
    RegimeActionStats,
    RegimeEntryStats,
    RegimePerformanceArtifacts,
    RegimeTemplateStats,
)


@dataclass(frozen=True)
class RegimeDriftSignal:
    regime: RegimeCluster
    entity_type: str  # "template", "entry", "action", "risk"
    entity_id: str
    severity: str  # "info", "warning", "critical"
    reason: str
    metrics_before: Dict[str, Any]
    metrics_after: Dict[str, Any]
    metadata: Dict[str, Any]


def _severity(ev_drop: float, wr_drop: float, dd_increase: float) -> str:
    if ev_drop > 0.5 or wr_drop > 0.2 or dd_increase > 0.5:
        return "critical"
    if ev_drop > 0.2 or wr_drop > 0.1 or dd_increase > 0.2:
        return "warning"
    return "info"


def _compare_stat(
    before, after, entity_type: str, entity_id: str
) -> RegimeDriftSignal | None:
    ev_drop = (before.avg_ev - after.avg_ev) if after else 0.0
    wr_drop = (before.winrate - after.winrate) if after else 0.0
    dd_increase = (after.avg_drawdown - before.avg_drawdown) if after else 0.0

    if ev_drop <= 0 and wr_drop <= 0 and dd_increase <= 0:
        return None

    sev = _severity(ev_drop, wr_drop, dd_increase)
    reason = (
        f"ev_drop={ev_drop:.2f}; wr_drop={wr_drop:.2f}; dd_increase={dd_increase:.2f}"
    )
    return RegimeDriftSignal(
        regime=before.regime,
        entity_type=entity_type,
        entity_id=entity_id,
        severity=sev,
        reason=reason,
        metrics_before=asdict(before),
        metrics_after=asdict(after) if after else {},
        metadata={},
    )


def _index_by_key(stats: Dict[str, Any], key_fn) -> Dict[str, Any]:
    return {key_fn(v): v for v in stats.values()}


def compute_regime_drift(
    perf_before: RegimePerformanceArtifacts,
    perf_after: RegimePerformanceArtifacts,
) -> List[RegimeDriftSignal]:
    signals: List[RegimeDriftSignal] = []

    tmpl_before = _index_by_key(
        perf_before.template_stats, lambda s: (s.regime, s.template_id)
    )
    tmpl_after = _index_by_key(
        perf_after.template_stats, lambda s: (s.regime, s.template_id)
    )

    for key, bstat in tmpl_before.items():
        astat = tmpl_after.get(key)
        sig = _compare_stat(bstat, astat, "template", bstat.template_id)
        if sig:
            signals.append(sig)

    entry_before = _index_by_key(
        perf_before.entry_stats, lambda s: (s.regime, s.entry_model_id)
    )
    entry_after = _index_by_key(
        perf_after.entry_stats, lambda s: (s.regime, s.entry_model_id)
    )
    for key, bstat in entry_before.items():
        astat = entry_after.get(key)
        sig = _compare_stat(bstat, astat, "entry", bstat.entry_model_id)
        if sig:
            signals.append(sig)

    action_before = _index_by_key(
        perf_before.action_stats, lambda s: (s.regime, s.action_type)
    )
    action_after = _index_by_key(
        perf_after.action_stats, lambda s: (s.regime, s.action_type)
    )
    for key, bstat in action_before.items():
        astat = action_after.get(key)
        # Treat winrate as proxy for effectiveness; variance/tail risk shift could be added similarly
        sig = _compare_stat(bstat, astat, "action", bstat.action_type)
        if sig:
            signals.append(sig)

    # Risk drift: if tail risk or drawdown increased notably
    for key, bstat in tmpl_before.items():
        astat = tmpl_after.get(key)
        if not astat:
            continue
        dd_increase = astat.avg_drawdown - bstat.avg_drawdown
        tail_increase = astat.tail_risk - bstat.tail_risk
        if dd_increase > 0.3 or tail_increase > 0.3:
            sev = "critical" if dd_increase > 0.5 or tail_increase > 0.5 else "warning"
            reason = f"risk_drift dd={dd_increase:.2f} tail={tail_increase:.2f}"
            signals.append(
                RegimeDriftSignal(
                    regime=bstat.regime,
                    entity_type="risk",
                    entity_id=bstat.template_id,
                    severity=sev,
                    reason=reason,
                    metrics_before=asdict(bstat),
                    metrics_after=asdict(astat),
                    metadata={},
                )
            )

    # News-specific misalignment heuristics
    for key, bstat in tmpl_before.items():
        if bstat.regime == RegimeCluster.NEWS_SHOCK_EXPLOSION:
            astat = tmpl_after.get(key)
            if astat and astat.count > bstat.count:
                signals.append(
                    RegimeDriftSignal(
                        regime=bstat.regime,
                        entity_type="template",
                        entity_id=bstat.template_id,
                        severity="warning",
                        reason="too_aggressive_during_news_shock",
                        metrics_before=asdict(bstat),
                        metrics_after=asdict(astat),
                        metadata={},
                    )
                )
            elif astat and astat.avg_ev < bstat.avg_ev:
                signals.append(
                    RegimeDriftSignal(
                        regime=bstat.regime,
                        entity_type="template",
                        entity_id=bstat.template_id,
                        severity="info",
                        reason="news_shock_ev_decline",
                        metrics_before=asdict(bstat),
                        metrics_after=asdict(astat),
                        metadata={},
                    )
                )
        if bstat.regime == RegimeCluster.NEWS_POST_DIGESTION_TREND:
            astat = tmpl_after.get(key)
            if astat and astat.avg_ev < bstat.avg_ev - 0.1:
                signals.append(
                    RegimeDriftSignal(
                        regime=bstat.regime,
                        entity_type="template",
                        entity_id=bstat.template_id,
                        severity="info",
                        reason="too_passive_post_digest",
                        metrics_before=asdict(bstat),
                        metrics_after=asdict(astat),
                        metadata={},
                    )
                )

    severity_rank = {"critical": 0, "warning": 1, "info": 2}
    signals.sort(
        key=lambda s: (
            s.regime.value,
            s.entity_type,
            s.entity_id,
            severity_rank.get(s.severity, 3),
        )
    )

    payload = [
        {
            **{
                "regime": s.regime.value,
            },
            **{
                k: (v.value if isinstance(v, RegimeCluster) else v)
                for k, v in asdict(s).items()
                if k != "regime"
            },
        }
        for s in signals
    ]
    Path("storage/reports/regime").mkdir(parents=True, exist_ok=True)
    Path("storage/reports/regime/regime_drift_report.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return signals
