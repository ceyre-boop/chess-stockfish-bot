import pytest
from data.unified_feed import UnifiedFeed
from engine.decision_frame import DecisionFrame
from engine.ev_brain_model import EVBrainV1
from engine.entry_brain import BrainPolicy
from engine.opening_book import OpeningBookV1
from engine.endgame_tablebases import EndgameTablebasesV1
from engine.search_engine_v1 import SearchEngineV1
from engine.runtime_safety_envelope import RuntimeSafetyEnvelope
from engine.realtime_decision_loop import RealtimeDecisionLoop
from engine.live_modes import LiveMode

# 1. Instantiate all required engine components with real artifacts
# (Assume real artifacts are available at default locations or as part of the codebase)

def test_full_engine_real_data():
    # UnifiedFeed: load real data
    feed = UnifiedFeed(source="polygon", symbol="AAPL")
    events = feed.load_historical({"date": "2024-10-15", "timespan": "minute"})
    assert events, "No real data events loaded."
    event = events[0]
    # DecisionFrame expects tick, book, market fields
    frame = DecisionFrame(
        tick=event["tick"],
        book=event["book"],
        market=event["market"]
    )

    # Instantiate engine stack with real artifacts
    ev_brain = EVBrainV1.load("storage/ev_brain_v1.json")
    brain_policy = BrainPolicy()
    opening_book = OpeningBookV1()
    tablebases = EndgameTablebasesV1()
    search_engine = SearchEngineV1(
        ev_brain=ev_brain,
        brain_policy=brain_policy,
        opening_book=opening_book,
        tablebases=tablebases
    )
    safety_envelope = RuntimeSafetyEnvelope()
    mode = LiveMode.SIM_REPLAY
    loop = RealtimeDecisionLoop(
        search_engine=search_engine,
        brain_policy=brain_policy,
        mode=mode,
        safety_envelope=safety_envelope
    )

    # 3. Run the full engine pipeline
    # The run_once API expects market_state, position_state, clock_state, risk_envelope
    market_state = event
    position_state = {}
    clock_state = {"timestamp_utc": event["tick"]["timestamp"]}
    risk_envelope = {}
    result1 = loop.run_once(market_state, position_state, clock_state, risk_envelope)
    result2 = loop.run_once(market_state, position_state, clock_state, risk_envelope)

    # 4. Print required fields
    print("ACTION:", result1.get("action"))
    print("regime_cluster:", result1.get("metadata", {}).get("regime_cluster"))
    print("participant_likelihoods:", result1.get("metadata", {}).get("participant_likelihoods"))
    print("ev_features:", result1.get("metadata", {}).get("ev_features"))
    print("search_weights:", result1.get("metadata", {}).get("search_weights"))
    print("risk_envelope:", result1.get("metadata", {}).get("risk_envelope"))
    print("participant_risk_limits:", result1.get("metadata", {}).get("participant_risk_limits"))
    print("policy_labels:", result1.get("metadata", {}).get("policy_labels"))
    print("safety_flags:", result1.get("metadata", {}).get("safety_flags"))

    # 5. Assertions
    assert result1 == result2, "Results must be deterministic across runs"
    required_keys = [
        "regime_cluster",
        "participant_likelihoods",
        "ev_features",
        "search_weights",
        "risk_envelope",
        "participant_risk_limits",
    ]
    for key in required_keys:
        assert key in result1.get("metadata", {}), f"Missing metadata key: {key}"
        assert result1["metadata"][key] is not None, f"Metadata key {key} must not be None"
    if "safety_flags" in result1.get("metadata", {}):
        for flag, triggered in result1["metadata"]["safety_flags"].items():
            assert triggered is False or triggered is True
    # No synthetic fields
    for k in result1.get("metadata", {}):
        assert not k.startswith("synthetic"), f"Synthetic field {k} found in metadata"
    # No exceptions (pytest will fail if any exception is raised)
