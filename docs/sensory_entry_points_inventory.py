"""
Auto-generated inventory of sensory entry points (Phase 1.1)

This file is a machine- and human-readable map of every place in the
repo that pulls, constructs, or injects market data (ticks/bars/replays).
Do NOT modify runtime behavior here — this is discovery only.
"""

SENSORY_ENTRY_POINTS = [
    {
        "module": "adapters.mt5_adapter",
        "object": "init_mt5_from_env",
        "type": "function",
        "role": "mt5_initialization",
        "provider": "mt5",
        "classification": "KEEP",
        "notes": "Initializes MT5 connection from env; adapter-level init helper."
    },
    {
        "module": "adapters.mt5_adapter",
        "object": "get_historical_bars_mt5",
        "type": "function",
        "role": "historical_bars_mt5",
        "provider": "mt5",
        "classification": "KEEP",
        "notes": "Fetches MT5 historical bars and converts to primitive canonical dicts."
    },
    {
        "module": "adapters.mt5_adapter",
        "object": "get_latest_tick",
        "type": "function",
        "role": "latest_tick",
        "provider": "mt5",
        "classification": "KEEP",
        "notes": "Returns a canonical tick dict by wrapping MetaTrader5.symbol_info_tick."
    },
    {
        "module": "adapters.mt5_adapter",
        "object": "get_latest_snapshot",
        "type": "function",
        "role": "latest_snapshot",
        "provider": "mt5",
        "classification": "KEEP",
        "notes": "Primary adapter API: returns canonical snapshot dict conforming to canonical_schema." 
    },
    {
        "module": "adapters.alpaca_adapter",
        "object": "get_historical_bars",
        "type": "function",
        "role": "historical_bars_alpaca",
        "provider": "alpaca",
        "classification": "KEEP",
        "notes": "Calls Alpaca HTTP API, normalizes bars to canonical dicts."
    },
    {
        "module": "adapters.alpaca_adapter",
        "object": "get_latest_snapshot",
        "type": "function",
        "role": "latest_snapshot",
        "provider": "alpaca",
        "classification": "KEEP",
        "notes": "Primary adapter API: returns canonical snapshot dict conforming to canonical_schema." 
    },
    {
        "module": "adapters.polygon_adapter",
        "object": "get_historical_bars",
        "type": "function",
        "role": "historical_bars_polygon",
        "provider": "polygon",
        "classification": "KEEP",
        "notes": "Fetches Polygon aggregates and normalizes into canonical bars."
    },
    {
        "module": "adapters.polygon_adapter",
        "object": "stream_live",
        "type": "function",
        "role": "polygon_live_stream",
        "provider": "polygon",
        "classification": "KEEP",
        "notes": "REST-polling live stream (NBBO) producing canonical tick-like dicts."
    },
    {
        "module": "adapters.polygon_adapter",
        "object": "get_nbbo_quotes",
        "type": "function",
        "role": "nbbo_quote_lookup",
        "provider": "polygon",
        "classification": "KEEP",
        "notes": "Helper that fetches NBBO quote(s) for historical normalization."
    },
    {
        "module": "adapters.polygon_adapter",
        "object": "get_latest_snapshot",
        "type": "function",
        "role": "latest_snapshot",
        "provider": "polygon",
        "classification": "KEEP",
        "notes": "Primary adapter API: maps latest Polygon bar to canonical snapshot dict." 
    },
    {
        "module": "adapters.market_data_router",
        "object": "get_unified_bars",
        "type": "function",
        "role": "router_dual_feed",
        "provider": "mixed",
        "classification": "KEEP",
        "notes": "Router: prefer Polygon, fallback to Alpaca; returns validated bars."
    },
    {
        "module": "adapters.market_data_router",
        "object": "get_historical_bars_dual_feed",
        "type": "function",
        "role": "alias_dual_feed",
        "provider": "mixed",
        "classification": "KEEP",
        "notes": "Alias for get_unified_bars for dual-feed usage."
    },
    {
        "module": "adapters.asset_class_router",
        "object": "get_historical_bars_asset_routed",
        "type": "function",
        "role": "asset_routing",
        "provider": "mixed",
        "classification": "KEEP",
        "notes": "Routes asset classes to Polygon/Alpaca or MT5 historical adapters."
    },
    {
        "module": "data.unified_feed",
        "object": "UnifiedFeed.load_historical",
        "type": "function",
        "role": "unified_historical_loader",
        "provider": "mixed",
        "classification": "KEEP",
        "notes": "Unified loader for historical ticks/bars; supports polygon, mt5, scenario."
    },
    {
        "module": "data.unified_feed",
        "object": "UnifiedFeed.stream",
        "type": "function",
        "role": "unified_live_stream",
        "provider": "mixed",
        "classification": "KEEP",
        "notes": "Unified live stream generator that canonicalizes and enforces monotonicity."
    },
    {
        "module": "data.unified_feed",
        "object": "get_snapshot",
        "type": "function",
        "role": "provider_router",
        "provider": "mixed",
        "classification": "KEEP",
        "notes": "Router: deterministic provider priority; returns canonical snapshot via adapters.get_latest_snapshot."
    },
    {
        "module": "data.polygon_adapter",
        "object": "stream_live",
        "type": "function",
        "role": "polygon_live_stream_alternate",
        "provider": "polygon",
        "classification": "WRAP",
        "notes": "Alternate polygon adapter implementation under data/; duplicates live ingestion."
    },
    {
        "module": "data.mt5_adapter",
        "object": "stream_live",
        "type": "function",
        "role": "mt5_live_stream_alternate",
        "provider": "mt5",
        "classification": "WRAP",
        "notes": "Alternate MT5 adapter (data/) with streaming generator; duplicate of adapters/ layer."
    },
    {
        "module": "mt5.live_feed",
        "object": "MT5LiveFeed.get_tick",
        "type": "function",
        "role": "engine_feed_get_tick",
        "provider": "mt5",
        "classification": "WRAP",
        "notes": "Engine-facing MT5 feed; returns canonical primitive tick dicts. (now WRAP; unified_feed is canonical router)"
    },
    {
        "module": "mt5.live_feed",
        "object": "MT5LiveFeed.get_candles",
        "type": "function",
        "role": "engine_feed_get_candles",
        "provider": "mt5",
        "classification": "WRAP",
        "notes": "Engine-facing candles reader; wraps MT5 candle APIs and normalizes output. (WRAP)"
    },
    {
        "module": "mt5.live_feed",
        "object": "initialize_feed",
        "type": "function",
        "role": "engine_feed_singleton_init",
        "provider": "mt5",
        "classification": "KEEP",
        "notes": "Helper that constructs a global MT5LiveFeed instance for engine use."
    },
    {
        "module": "mt5.live_feed",
        "object": "get_feed",
        "type": "function",
        "role": "engine_feed_singleton_get",
        "provider": "mt5",
        "classification": "KEEP",
        "notes": "Returns or initializes the global MT5LiveFeed instance."
    },
    {
        "module": "loop.realtime",
        "object": "_fetch_market_data",
        "type": "function",
        "role": "engine_loop_data_pull",
        "provider": "mixed",
        "classification": "WRAP",
        "notes": "Engine loop helper that now pulls canonical snapshots via data.unified_feed.get_snapshot."
    },
    {
        "module": "loop.realtime",
        "object": "run_iteration",
        "type": "function",
        "role": "engine_loop_iteration",
        "provider": "mixed",
        "classification": "WRAP",
        "notes": "Main realtime iteration that now obtains canonical snapshots from data.unified_feed and drives state builder."
    },
    {
        "module": "state.state_builder",
        "object": "fetch_tick_data",
        "type": "function",
        "role": "state_builder_tick_fetch",
        "provider": "mixed",
        "classification": "KEEP",
        "notes": "State builder sensory entry point: now calls data.unified_feed.get_snapshot and consumes canonical snapshots only."
    },
    {
        "module": "state.state_builder",
        "object": "fetch_candles",
        "type": "function",
        "role": "state_builder_candles",
        "provider": "mt5",
        "classification": "WRAP",
        "notes": "Currently calls MT5 candle APIs (mt5.copy_rates_from_pos); should be routed via adapters."
    },
    {
        "module": "state.state_builder",
        "object": "_mock_tick_data",
        "type": "function",
        "role": "disabled_mock_provider",
        "provider": "replay",
        "classification": "KILL",
        "notes": "Mock tick generator explicitly disabled (raises RuntimeError); legacy mock path."
    },
    {
        "module": "mt5.orders",
        "object": "MockTickData",
        "type": "class",
        "role": "mock_tick_dataclass",
        "provider": "replay",
        "classification": "WRAP",
        "notes": "Dataclass used to create mock ticks; used by MT5 orders mock paths (returns canonical via to_canonical())."
    },
    {
        "module": "mt5.orders",
        "object": "MT5Orders._mock_tick",
        "type": "function",
        "role": "orders_mock_tick",
        "provider": "replay",
        "classification": "WRAP",
        "notes": "Orders module fallback that returns a primitive canonical mock tick for demo/testing."
    },
    {
        "module": "legacy.mt5_live_feed_mock",
        "object": "mock_tick",
        "type": "function",
        "role": "legacy_mock_tick",
        "provider": "replay",
        "classification": "KILL",
        "notes": "Legacy test-only mock generator moved to legacy/; must not be imported by runtime."
    },
    {
        "module": "legacy.mt5_live_feed_mock",
        "object": "mock_candles",
        "type": "function",
        "role": "legacy_mock_candles",
        "provider": "replay",
        "classification": "KILL",
        "notes": "Legacy mock candle generator for tests/offline tooling; quarantine in legacy/."
    },
    {
        "module": "compare_providers",
        "object": "get_alpaca_bars",
        "type": "function",
        "role": "one-off_script_alpaca_pull",
        "provider": "alpaca",
        "classification": "WRAP",
        "notes": "Utility script that imports alpaca_trade_api directly for ad-hoc comparisons."
    },
    {
        "module": "compare_providers_http",
        "object": "get_alpaca_daily_bars",
        "type": "function",
        "role": "one-off_script_alpaca_http",
        "provider": "alpaca",
        "classification": "WRAP",
        "notes": "HTTP-based utility that calls Alpaca via alpaca_trade_api for ad-hoc tasks."
    },
    {
        "module": "live_candle_visualizer",
        "object": "module",
        "type": "script",
        "role": "visualizer_script",
        "provider": "alpaca",
        "classification": "WRAP",
        "notes": "Standalone script using Alpaca SDK to render live candles; not engine runtime."
    },
    {
        "module": "stockfish_candle_printer",
        "object": "module",
        "type": "script",
        "role": "printer_script",
        "provider": "alpaca",
        "classification": "WRAP",
        "notes": "Ad-hoc script that pulls via Alpaca SDK for display/analysis."
    },
    {
        "module": "alpaca_1min_candle_pull",
        "object": "module",
        "type": "script",
        "role": "data_pull_script",
        "provider": "alpaca",
        "classification": "WRAP",
        "notes": "Utility to pull 1-minute Alpaca candles; ad-hoc tooling."
    },
    {
        "module": "run_live_smoke_test",
        "object": "module",
        "type": "script",
        "role": "smoke_test_runner",
        "provider": "mixed",
        "classification": "WRAP",
        "notes": "Script that composes provider adapters for smoke testing (Polygon/Alpaca/MT5)."
    },
    {
        "module": "live_ingestion_smoke_test",
        "object": "module",
        "type": "script",
        "role": "ingestion_smoke",
        "provider": "mixed",
        "classification": "WRAP",
        "notes": "Local smoke test harness for live ingestion paths."
    },
    {
        "module": "tests_live.test_mt5_adapter_smoke",
        "object": "module",
        "type": "script",
        "role": "integration_test_live_mt5",
        "provider": "mt5",
        "classification": "WRAP",
        "notes": "Integration test that attempts safe mt5 stream interactions; exercises live code paths."
    },
    {
        "module": "tests_live.test_mt5_ticks_and_candles",
        "object": "module",
        "type": "script",
        "role": "integration_test_mt5_ticks",
        "provider": "mt5",
        "classification": "WRAP",
        "notes": "Live test that inspects MT5 tick and candle APIs; pulls data in test context."
    },
    {
        "module": "tests_live.test_polygon_daily",
        "object": "module",
        "type": "script",
        "role": "integration_test_polygon",
        "provider": "polygon",
        "classification": "WRAP",
        "notes": "Live test hitting polygon historical endpoints for validation."
    },
    {
        "module": "tests_live.test_alpaca_intraday",
        "object": "module",
        "type": "script",
        "role": "integration_test_alpaca",
        "provider": "alpaca",
        "classification": "WRAP",
        "notes": "Live test that pulls intraday data from Alpaca for validation."
    },
]

def _summary():
    counts = {"KEEP":0, "WRAP":0, "KILL":0}
    for e in SENSORY_ENTRY_POINTS:
        counts[e.get("classification", "WRAP")] = counts.get(e.get("classification"), 0) + 1
    return {"total": len(SENSORY_ENTRY_POINTS), "by_class": counts}

def _group_by_provider(entries):
    by_provider = {}
    for e in entries:
        p = e.get("provider", "unknown")
        by_provider.setdefault(p, []).append(e.get("module"))
    return by_provider


def _validate_and_expand():
    """Scan repo for provider/tick/bar/replay patterns and add any missing files.

    - If files containing provider SDK calls or tick/bar constructors are found
      but not present in SENSORY_ENTRY_POINTS, they are appended with a
      conservative WRAP classification and reported.
    """
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    patterns = [
        r"alpaca",
        r"alpaca_trade_api",
        r"metatrader5",
        r"\bmt5\b",
        r"polygon",
        r"symbol_info_tick",
        r"copy_rates",
        r"stream_live",
        r"to_canonical\(|mock_tick|mock_candles",
        r"TickData|CandleData",
        r"replay|scenario|synthetic|demo",
        r"bar|candle|ohlc|ohclv|ohlcv",
    ]
    pattern = re.compile("(" + ")|(".join(patterns) + ")", re.IGNORECASE)

    # Build quick lookup of existing modules strings for simple matching
    existing = [e.get("module") for e in SENSORY_ENTRY_POINTS]

    discovered = []
    added = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in (".venv", "venv", "env", "__pycache__") for part in p.parts):
            continue
        if p.suffix.lower() not in (".py", ".ps1", ".md"):
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if pattern.search(txt):
            rel = str(p.relative_to(root)).replace('\\', '/')
            discovered.append(rel)
            matched = any((rel in m) or (m in rel) for m in existing)
            if not matched:
                # Infer provider
                low = txt.lower()
                if "metatrader5" in low or "mt5" in low:
                    prov = "mt5"
                elif "alpaca" in low:
                    prov = "alpaca"
                elif "polygon" in low:
                    prov = "polygon"
                elif any(k in low for k in ("mock", "scenario", "replay", "synthetic", "legacy")):
                    prov = "replay"
                else:
                    prov = "unknown"

                entry = {
                    "module": rel,
                    "object": "module",
                    "type": "script",
                    "role": "discovered_sensory_path",
                    "provider": prov,
                    "classification": "WRAP",
                    "notes": "Discovered by repo scan; conservative WRAP."
                }
                SENSORY_ENTRY_POINTS.append(entry)
                added.append(entry)

    # Validation: ensure no provider SDK calls exist outside inventory
    violations = []
    for rel in discovered:
        in_inventory = any((rel in e.get("module")) or (e.get("module") in rel) for e in SENSORY_ENTRY_POINTS)
        if not in_inventory:
            violations.append(rel)

    return {"discovered_count": len(discovered), "added_count": len(added), "added": added, "violations": violations}

def check_schema_coverage(entries):
    """Check that KEEP/WRAP entries can be mapped to the canonical schema.

    Uses lightweight heuristics and the `data.canonical_schema` utilities to
    construct a minimal sample snapshot for each entry and validate it.
    Returns list of warning messages.
    """
    warnings = []
    try:
        from data import canonical_schema as cs
    except Exception:
        warnings.append("could not import data.canonical_schema; schema checks skipped")
        return warnings

    for e in entries:
        cls = e.get('classification')
        if cls not in ('KEEP', 'WRAP'):
            continue
        mod = e.get('module')
        provider = e.get('provider', 'unknown')

        # Build minimal snapshot candidate
        sample = {
            'symbol': 'TEST',
            'provider': provider if provider else 'unknown',
            'timestamp': 1600000000.0,
            'price': 1.0,
            'bid': None,
            'ask': None,
            'spread': None,
            'volume': None,
            'bar': {'open': None, 'high': None, 'low': None, 'close': None, 'volume': None, 'tf': None},
            'quality': {'stale': False, 'synthetic': False, 'partial': False},
        }

        # If entry indicates candles, populate bar values
        lname = (e.get('object','') + ' ' + e.get('role','')).lower()
        if 'candle' in lname or 'bar' in lname or 'candles' in lname:
            sample['bar'] = {'open': 1.0, 'high': 1.1, 'low': 0.9, 'close': 1.0, 'volume': 100.0, 'tf': '1m'}
        else:
            # tick-like: set bid/ask/price
            sample['bid'] = 0.99
            sample['ask'] = 1.01
            sample['spread'] = round(sample['ask'] - sample['bid'], 12)
            sample['price'] = 1.0

        sample = cs.canonicalize_missing_fields(sample)
        ok = cs.validate_snapshot(sample)
        if not ok:
            try:
                cs.assert_snapshot(sample)
            except AssertionError as ex:
                warnings.append(f"Schema problem for {mod}::{e.get('object')}: {ex}")
            except Exception as ex:
                warnings.append(f"Schema unknown failure for {mod}::{e.get('object')}: {ex}")

        # Warn on non-primary providers (informational)
        if provider not in cs.PRIMARY_PROVIDERS and provider not in ('mixed', 'unknown'):
            warnings.append(f"Provider '{provider}' for {mod} is unusual; expected one of {cs.PRIMARY_PROVIDERS}")

    return warnings


def _print_summary():
    summary = _summary()
    print("\nSensory Entry Points Inventory")
    print("Total:", summary["total"]) 
    print("By classification:")
    for k, v in summary["by_class"].items():
        print(f"  - {k}: {v}")
    print()
    byprov = _group_by_provider(SENSORY_ENTRY_POINTS)
    print("Modules by provider:")
    for prov, mods in byprov.items():
        print(f"  - {prov}: {len(mods)} modules")
        for m in mods:
            print(f"      * {m}")

    print()
    print("Running repo validation scan...")
    res = _validate_and_expand()
    print(f"Discovered files matching patterns: {res['discovered_count']}")
    print(f"New entries added to inventory: {res['added_count']}")
    if res['added_count'] > 0:
        print("Added modules:")
        for a in res['added']:
            print(f"  - {a['module']} (provider={a['provider']})")
    if res['violations']:
        print("Potential violations (files with patterns not present in inventory):")
        for v in res['violations']:
            print(f"  - {v}")


if __name__ == '__main__':
    _print_summary()

def build_clean_inventory() -> list:
    """Construct a cleaned, normalized sensory entry point list.

    Heuristics:
    - Keep adapter modules that emit canonical dicts in `adapters/`.
    - Keep unified feed/router modules in `data/` and `adapters/`.
    - Wrap data/ duplicates and one-off scripts that call provider SDKs.
    - Kill legacy mocks under `legacy/`.
    - Include test live scripts as WRAP.
    """
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    from pathlib import Path
    import re

    root = Path(__file__).resolve().parents[1]

    def module_name(p: Path) -> str:
        rel = p.relative_to(root).as_posix()
        if rel.endswith('.py'):
            rel = rel[:-3]
        return rel.replace('/', '.')

    cleaned = []

    # Curated canonical entries (explicit KEEP/WRAP/KILL) — conservative minimal set
    curated = [
        ("adapters.mt5_adapter", "get_latest_tick", "function", "primary_live_tick", "mt5", "KEEP", "Returns canonical tick dict wrapping MetaTrader5."),
        ("adapters.mt5_adapter", "get_historical_bars_mt5", "function", "historical_bars", "mt5", "KEEP", "Fetches MT5 historical bars and canonicalizes output."),
        ("adapters.mt5_adapter", "init_mt5_from_env", "function", "mt5_initialization", "mt5", "KEEP", "Initializes MT5 connection from environment for adapter use."),
        ("adapters.alpaca_adapter", "get_historical_bars", "function", "historical_bars", "alpaca", "KEEP", "Fetches Alpaca historical bars and normalizes to canonical dicts."),
        ("adapters.polygon_adapter", "get_historical_bars", "function", "historical_bars", "polygon", "KEEP", "Fetches Polygon historical bars and normalizes."),
        ("adapters.polygon_adapter", "stream_live", "function", "polygon_live_stream", "polygon", "KEEP", "Polygon live NBBO stream yielding canonical ticks."),
        ("adapters.market_data_router", "get_unified_bars", "function", "router_dual_feed", "mixed", "KEEP", "Router that prefers Polygon and falls back to Alpaca."),
        ("adapters.asset_class_router", "get_historical_bars_asset_routed", "function", "asset_routing", "mixed", "KEEP", "Routes asset classes to MT5 or dual-feed adapters."),
        ("data.unified_feed", "UnifiedFeed.load_historical", "function", "unified_historical_loader", "mixed", "KEEP", "Unified loader for historical ticks; enforces canonical shape."),
        ("data.unified_feed", "UnifiedFeed.stream", "function", "unified_live_stream", "mixed", "KEEP", "Unified live stream generator enforcing canonical ticks."),
        ("mt5.live_feed", "MT5LiveFeed.get_tick", "function", "engine_feed_get_tick", "mt5", "WRAP", "Engine-facing MT5 feed returning canonical tick dicts."),
        ("mt5.live_feed", "MT5LiveFeed.get_candles", "function", "engine_feed_get_candles", "mt5", "WRAP", "Engine-facing candles reader, returns primitive candle dicts."),
        ("mt5.live_feed", "initialize_feed", "function", "engine_feed_singleton_init", "mt5", "KEEP", "Helper to initialize global MT5LiveFeed instance."),
        ("mt5.live_feed", "get_feed", "function", "engine_feed_singleton_get", "mt5", "KEEP", "Returns or initializes MT5LiveFeed singleton."),
        ("state.state_builder", "fetch_tick_data", "function", "state_builder_tick_fetch", "mixed", "KEEP", "State builder sensory entry point: uses data.unified_feed.get_snapshot for canonical snapshots."),
        ("state.state_builder", "fetch_candles", "function", "state_builder_candles", "mt5", "WRAP", "Currently uses MT5 candle APIs; should be routed via adapters."),
        ("legacy.mt5_live_feed_mock", "mock_tick", "function", "legacy_mock_tick", "replay", "KILL", "Legacy test-only mock tick generator; quarantine in legacy/."),
        ("legacy.mt5_live_feed_mock", "mock_candles", "function", "legacy_mock_candles", "replay", "KILL", "Legacy mock candle generator for tests/offline tooling; quarantine."),
        ("mt5.orders", "MockTickData", "class", "mock_tick_dataclass", "replay", "WRAP", "Dataclass used to create mock ticks; use to_canonical() for primitive dict."),
        ("mt5.orders", "MT5Orders._mock_tick", "function", "orders_mock_tick", "replay", "WRAP", "Orders module mock tick generator returning canonical dict via dataclass."),
    ]

    for item in curated:
        if len(item) == 7:
            mod, obj, typ, role, prov, cls, notes = item
        else:
            continue
        cleaned.append({
            "module": mod,
            "object": obj,
            "type": typ,
            "role": role,
            "provider": prov,
            "classification": cls,
            "notes": notes,
        })

    # Strict discovery: only include .py files that actually contain provider SDK calls
    provider_markers = [
        r"alpaca_trade_api",
        r"MetaTrader5",
        r"metatrader5",
        r"symbol_info_tick",
        r"copy_rates",
        r"copy_rates_from_pos",
        r"copy_rates_range",
        r"polygon",
        r"POLYGON",
        r"stream_live",
        r"to_canonical",
        r"mock_tick",
        r"mock_candles",
        r"TickData",
        r"Candle",
    ]
    provider_re = re.compile("(" + ")|(".join(provider_markers) + ")", re.IGNORECASE)

    # Exclude noisy locations entirely
    exclude_dirs = ("docs/", "examples/", "notebooks/", "scripts/", ".venv", "venv", "env", "__pycache__")

    for p in root.rglob("*.py"):
        rel = p.relative_to(root).as_posix()
        if any(rel.startswith(d) for d in exclude_dirs):
            continue
        try:
            txt = p.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        if not provider_re.search(txt):
            continue

        # Module candidate contains provider marker — include it
        mod = module_name(p)
        # Skip duplicates
        if any(e['module'] == mod for e in cleaned):
            continue

        low = txt.lower()
        prov = 'unknown'
        if 'metatrader5' in low or 'mt5' in low:
            prov = 'mt5'
        elif 'alpaca' in low:
            prov = 'alpaca'
        elif 'polygon' in low:
            prov = 'polygon'
        elif any(k in low for k in ('mock', 'scenario', 'replay', 'synthetic', 'legacy')):
            prov = 'replay'

        # Conservative classification rules
        if rel.startswith('legacy/') or 'legacy' in rel or 'mock' in rel:
            cls = 'KILL'
        elif rel.startswith('adapters/') or rel.startswith('data/') or rel.startswith('mt5/'):
            # adapters/data/mt5 files are likely KEEP if not legacy
            cls = 'KEEP' if 'adapter' in p.name or 'live_feed' in rel or 'unified_feed' in rel else 'WRAP'
        else:
            cls = 'WRAP'

        # Tests: only include if they touch provider SDKs (we already filtered by marker)
        if rel.startswith('tests/'):
            cls = 'WRAP'

        cleaned.append({
            'module': mod,
            'object': 'module',
            'type': 'module',
            'role': 'discovered_sensory_module',
            'provider': prov,
            'classification': cls,
            'notes': 'Auto-included by strict scan: contains provider SDK/tick markers; review classification.'
        })

    # Deduplicate and normalize final list
    seen = set()
    final = []
    for e in cleaned:
        key = (e['module'], e['object'])
        if key in seen:
            continue
        seen.add(key)
        if e.get('provider') not in ('alpaca', 'mt5', 'polygon', 'replay', 'mixed', 'unknown'):
            e['provider'] = 'unknown'
        if e.get('classification') not in ('KEEP', 'WRAP', 'KILL'):
            e['classification'] = 'WRAP'
        final.append(e)

    # Validation pass: ensure any file with provider markers is present; add as WRAP if missing
    # (This closes gaps where module naming differs)
    for p in root.rglob('*.py'):
        rel = p.relative_to(root).as_posix()
        if any(rel.startswith(d) for d in exclude_dirs):
            continue
        try:
            txt = p.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        if not provider_re.search(txt):
            continue
        mod = module_name(p)
        if not any(entry['module'] == mod for entry in final):
            low = txt.lower()
            prov = 'unknown'
            if 'metatrader5' in low or 'mt5' in low:
                prov = 'mt5'
            elif 'alpaca' in low:
                prov = 'alpaca'
            elif 'polygon' in low:
                prov = 'polygon'
            final.append({
                'module': mod,
                'object': 'module',
                'type': 'module',
                'role': 'discovered_sensory_module',
                'provider': prov,
                'classification': 'WRAP',
                'notes': 'Added in validation pass; contains provider markers.'
            })

    return final


