from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from engine.pattern_templates import PatternFamily
from engine.regime.regime_cluster_model import RegimeCluster


@dataclass(frozen=True)
class RegimeTemplateStats:
    regime: RegimeCluster
    template_id: str
    eco_code: str
    family: PatternFamily
    count: int
    avg_ev: float
    winrate: float
    avg_mae: float
    avg_mfe: float
    avg_time_in_trade: float
    avg_drawdown: float
    variance: float
    tail_risk: float
    news_window: str  # "pre", "during", "post", "none"
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class RegimeEntryStats:
    regime: RegimeCluster
    entry_model_id: str
    count: int
    avg_ev: float
    winrate: float
    avg_mae: float
    avg_mfe: float
    avg_time_in_trade: float
    avg_drawdown: float
    variance: float
    tail_risk: float
    news_window: str
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class RegimeActionStats:
    regime: RegimeCluster
    action_type: str
    count: int
    avg_ev: float
    winrate: float
    avg_mae: float
    avg_mfe: float
    avg_time_in_trade: float
    avg_drawdown: float
    variance: float
    tail_risk: float
    news_window: str
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class RegimePerformanceArtifacts:
    template_stats: Dict[str, RegimeTemplateStats]
    entry_stats: Dict[str, RegimeEntryStats]
    action_stats: Dict[str, RegimeActionStats]
    metadata: Dict[str, Any]


class _Accumulator:
    def __init__(self) -> None:
        self.count = 0
        self.evs: List[float] = []
        self.realized: List[float] = []
        self.mae: List[float] = []
        self.mfe: List[float] = []
        self.time_in_trade: List[float] = []
        self.drawdown: List[float] = []

    def add(
        self, ev: float, realized: float, mae: float, mfe: float, tit: float, dd: float
    ) -> None:
        self.count += 1
        self.evs.append(ev)
        self.realized.append(realized)
        self.mae.append(mae)
        self.mfe.append(mfe)
        self.time_in_trade.append(tit)
        self.drawdown.append(dd)

    def finalize(self) -> Tuple[float, float, float, float, float, float, float]:
        if self.count == 0:
            return (0.0,) * 7
        avg_ev = sum(self.evs) / self.count
        winrate = sum(1 for r in self.realized if r > 0) / self.count
        avg_mae = sum(self.mae) / self.count
        avg_mfe = sum(self.mfe) / self.count
        avg_tit = sum(self.time_in_trade) / self.count
        avg_dd = sum(self.drawdown) / self.count
        variance = sum((ev - avg_ev) ** 2 for ev in self.evs) / self.count
        return avg_ev, winrate, avg_mae, avg_mfe, avg_tit, avg_dd, variance


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    q = min(1.0, max(0.0, p))
    ordered = sorted(values)
    idx = int(round(q * (len(ordered) - 1)))
    return ordered[idx]


def _normalize_regime(value: Any) -> RegimeCluster:
    if isinstance(value, RegimeCluster):
        return value
    return RegimeCluster(str(value))


def _normalize_family(value: Any) -> PatternFamily:
    if isinstance(value, PatternFamily):
        return value
    return PatternFamily(str(value))


def _require(record: Dict[str, Any], key: str) -> Any:
    if key not in record:
        raise ValueError(f"missing required field: {key}")
    return record[key]


def _news_window(raw: Any) -> str:
    if raw in {"pre", "during", "post", "none"}:
        return raw
    return "none"


def _build_key(*parts: Any) -> str:
    return "|".join(str(p) for p in parts)


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def build_regime_performance(
    decision_records: Iterable[Dict[str, Any]], outcomes: Iterable[Dict[str, Any]]
) -> RegimePerformanceArtifacts:
    records = list(decision_records)
    outs = list(outcomes)
    if len(records) != len(outs):
        raise ValueError("decision_records and outcomes length mismatch")

    tmpl_buckets: Dict[str, _Accumulator] = {}
    entry_buckets: Dict[str, _Accumulator] = {}
    action_buckets: Dict[str, _Accumulator] = {}
    tmpl_meta: Dict[str, Tuple[RegimeCluster, str, str, PatternFamily, str]] = {}
    entry_meta: Dict[str, Tuple[RegimeCluster, str, str]] = {}
    action_meta: Dict[str, Tuple[RegimeCluster, str, str]] = {}

    for rec, out in zip(records, outs):
        regime_raw = _require(rec, "regime_cluster")
        regime = _normalize_regime(regime_raw)
        news_w = _news_window(rec.get("news_window"))

        ev = _require(out, "ev")
        realized = _require(out, "realized_R")
        mae = _require(out, "mae")
        mfe = _require(out, "mfe")
        tit = _require(out, "time_in_trade")
        dd = _require(out, "drawdown")

        tmpl_id = rec.get("template_id")
        eco_code = rec.get("eco_code")
        family = rec.get("family")
        if tmpl_id and eco_code and family:
            fam_enum = _normalize_family(family)
            tkey = _build_key(regime.value, tmpl_id, eco_code, fam_enum.value, news_w)
            tmpl_buckets.setdefault(tkey, _Accumulator()).add(
                ev, realized, mae, mfe, tit, dd
            )
            tmpl_meta.setdefault(tkey, (regime, tmpl_id, eco_code, fam_enum, news_w))

        entry_model_id = rec.get("entry_model_id")
        if entry_model_id:
            ekey = _build_key(regime.value, entry_model_id, news_w)
            entry_buckets.setdefault(ekey, _Accumulator()).add(
                ev, realized, mae, mfe, tit, dd
            )
            entry_meta.setdefault(ekey, (regime, entry_model_id, news_w))

        action_type = rec.get("action_type")
        if action_type:
            akey = _build_key(regime.value, action_type, news_w)
            action_buckets.setdefault(akey, _Accumulator()).add(
                ev, realized, mae, mfe, tit, dd
            )
            action_meta.setdefault(akey, (regime, action_type, news_w))

    def _finalize_template_stats() -> Dict[str, RegimeTemplateStats]:
        out_stats: Dict[str, RegimeTemplateStats] = {}
        for key in sorted(tmpl_buckets.keys()):
            acc = tmpl_buckets[key]
            regime, tmpl_id, eco_code, fam_enum, news_w = tmpl_meta[key]
            avg_ev, winrate, avg_mae, avg_mfe, avg_tit, avg_dd, variance = (
                acc.finalize()
            )
            tail_risk = _percentile(acc.evs, 0.1)
            out_stats[key] = RegimeTemplateStats(
                regime=regime,
                template_id=tmpl_id,
                eco_code=eco_code,
                family=fam_enum,
                count=acc.count,
                avg_ev=avg_ev,
                winrate=winrate,
                avg_mae=avg_mae,
                avg_mfe=avg_mfe,
                avg_time_in_trade=avg_tit,
                avg_drawdown=avg_dd,
                variance=variance,
                tail_risk=tail_risk,
                news_window=news_w,
                metadata={},
            )
        return out_stats

    def _finalize_entry_stats() -> Dict[str, RegimeEntryStats]:
        out_stats: Dict[str, RegimeEntryStats] = {}
        for key in sorted(entry_buckets.keys()):
            acc = entry_buckets[key]
            regime, entry_model_id, news_w = entry_meta[key]
            avg_ev, winrate, avg_mae, avg_mfe, avg_tit, avg_dd, variance = (
                acc.finalize()
            )
            tail_risk = _percentile(acc.evs, 0.1)
            out_stats[key] = RegimeEntryStats(
                regime=regime,
                entry_model_id=entry_model_id,
                count=acc.count,
                avg_ev=avg_ev,
                winrate=winrate,
                avg_mae=avg_mae,
                avg_mfe=avg_mfe,
                avg_time_in_trade=avg_tit,
                avg_drawdown=avg_dd,
                variance=variance,
                tail_risk=tail_risk,
                news_window=news_w,
                metadata={},
            )
        return out_stats

    def _finalize_action_stats() -> Dict[str, RegimeActionStats]:
        out_stats: Dict[str, RegimeActionStats] = {}
        for key in sorted(action_buckets.keys()):
            acc = action_buckets[key]
            regime, action_type, news_w = action_meta[key]
            avg_ev, winrate, avg_mae, avg_mfe, avg_tit, avg_dd, variance = (
                acc.finalize()
            )
            tail_risk = _percentile(acc.evs, 0.1)
            out_stats[key] = RegimeActionStats(
                regime=regime,
                action_type=action_type,
                count=acc.count,
                avg_ev=avg_ev,
                winrate=winrate,
                avg_mae=avg_mae,
                avg_mfe=avg_mfe,
                avg_time_in_trade=avg_tit,
                avg_drawdown=avg_dd,
                variance=variance,
                tail_risk=tail_risk,
                news_window=news_w,
                metadata={},
            )
        return out_stats

    template_stats = _finalize_template_stats()
    entry_stats = _finalize_entry_stats()
    action_stats = _finalize_action_stats()

    artifacts = RegimePerformanceArtifacts(
        template_stats=template_stats,
        entry_stats=entry_stats,
        action_stats=action_stats,
        metadata={"count_records": len(records)},
    )

    # Persist artifacts deterministically
    storage_root = Path("storage/reports/regime")
    tmpl_payload = {k: _serialize_stat(v) for k, v in template_stats.items()}
    entry_payload = {k: _serialize_stat(v) for k, v in entry_stats.items()}
    action_payload = {k: _serialize_stat(v) for k, v in action_stats.items()}

    _write_json(storage_root / "regime_template_performance.json", tmpl_payload)
    _write_json(storage_root / "regime_entry_performance.json", entry_payload)
    _write_json(storage_root / "regime_action_performance.json", action_payload)

    return artifacts


def _serialize_stat(obj: Any) -> Dict[str, Any]:
    """Serialize Regime* dataclasses into primitive-only dicts.

    Avoid using asdict() or _asdict() to prevent leaking nested
    dataclasses or SDK objects. Convert RegimeCluster and PatternFamily
    to their string values.
    """
    # Handle template stats
    if isinstance(obj, RegimeTemplateStats):
        return {
            "regime": _normalize_regime(obj.regime).value,
            "template_id": obj.template_id,
            "eco_code": obj.eco_code,
            "family": _normalize_family(obj.family).value,
            "count": int(obj.count),
            "avg_ev": float(obj.avg_ev),
            "winrate": float(obj.winrate),
            "avg_mae": float(obj.avg_mae),
            "avg_mfe": float(obj.avg_mfe),
            "avg_time_in_trade": float(obj.avg_time_in_trade),
            "avg_drawdown": float(obj.avg_drawdown),
            "variance": float(obj.variance),
            "tail_risk": float(obj.tail_risk),
            "news_window": str(obj.news_window),
            "metadata": dict(obj.metadata) if obj.metadata is not None else {},
        }

    if isinstance(obj, RegimeEntryStats):
        return {
            "regime": _normalize_regime(obj.regime).value,
            "entry_model_id": obj.entry_model_id,
            "count": int(obj.count),
            "avg_ev": float(obj.avg_ev),
            "winrate": float(obj.winrate),
            "avg_mae": float(obj.avg_mae),
            "avg_mfe": float(obj.avg_mfe),
            "avg_time_in_trade": float(obj.avg_time_in_trade),
            "avg_drawdown": float(obj.avg_drawdown),
            "variance": float(obj.variance),
            "tail_risk": float(obj.tail_risk),
            "news_window": str(obj.news_window),
            "metadata": dict(obj.metadata) if obj.metadata is not None else {},
        }

    if isinstance(obj, RegimeActionStats):
        return {
            "regime": _normalize_regime(obj.regime).value,
            "action_type": obj.action_type,
            "count": int(obj.count),
            "avg_ev": float(obj.avg_ev),
            "winrate": float(obj.winrate),
            "avg_mae": float(obj.avg_mae),
            "avg_mfe": float(obj.avg_mfe),
            "avg_time_in_trade": float(obj.avg_time_in_trade),
            "avg_drawdown": float(obj.avg_drawdown),
            "variance": float(obj.variance),
            "tail_risk": float(obj.tail_risk),
            "news_window": str(obj.news_window),
            "metadata": dict(obj.metadata) if obj.metadata is not None else {},
        }

    # Fallback: attempt to coerce mapping-like objects to primitives
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if isinstance(v, (RegimeCluster, PatternFamily)):
                out[k] = v.value
            else:
                # keep primitives; for non-primitives, coerce to str
                if isinstance(v, (str, int, float, bool)) or v is None:
                    out[k] = v
                else:
                    out[k] = str(v)
        return out

    # Last-resort: convert attributes to primitives
    out = {}
    for attr in [a for a in dir(obj) if not a.startswith("_")]:
        try:
            val = getattr(obj, attr)
            if callable(val):
                continue
            if isinstance(val, (RegimeCluster, PatternFamily)):
                out[attr] = val.value
            elif isinstance(val, (str, int, float, bool)) or val is None:
                out[attr] = val
            else:
                out[attr] = str(val)
        except Exception:
            continue
    return out
