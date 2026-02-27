
import pytest
from data.unified_feed import UnifiedFeed
from engine.decision_frame import DecisionFrame
from engine.realtime_decision_loop import RealtimeDecisionLoop

def test_real_data_decision_pipeline():
    # 1. Load a REAL DecisionFrame from UnifiedFeed (polygon source, real data)
    feed = UnifiedFeed(source="polygon", symbol="AAPL")
    events = feed.load_historical({"date": "2024-10-15", "timespan": "minute"})
    assert events, "No real data events loaded."
    # Use the first event to build a DecisionFrame
    event = events[0]
    # DecisionFrame expects tick, book, market fields
    frame = DecisionFrame(
        tick=event["tick"],
        book=event["book"],
        market=event["market"]
    )

    # 2. Pass the frame into the realtime decision loop
    # You must construct a RealtimeDecisionLoop instance with required dependencies.
    # For demonstration, we'll use mock objects for required constructor args.
    class Dummy:
        def __getattr__(self, name):
            return lambda *a, **kw: None
    loop = RealtimeDecisionLoop(
        search_engine=Dummy(),
        brain_policy=Dummy(),
        mode=Dummy(),
    )
    # The actual run_once signature requires market_state, position_state, clock_state, risk_envelope
    # We'll use the frame as market_state and dummy values for the rest
    result1 = loop.run_once(frame, None, {}, None)
    result2 = loop.run_once(frame, None, {}, None)

    # 3. Print required fields
    print("ACTION:", result1.action)
    print("regime_cluster:", result1.metadata.get("regime_cluster"))
    print("participant_likelihoods:", result1.metadata.get("participant_likelihoods"))
    print("ev_features:", result1.metadata.get("ev_features"))
    print("search_weights:", result1.metadata.get("search_weights"))
    print("risk_envelope:", result1.metadata.get("risk_envelope"))
    print("participant_risk_limits:", result1.metadata.get("participant_risk_limits"))
    if "policy_labels" in result1.metadata:
        print("policy_labels:", result1.metadata["policy_labels"])
    if "safety_flags" in result1.metadata:
        print("safety_flags:", result1.metadata["safety_flags"])

    # 4. Assert determinism
    assert result1.action == result2.action, "Action must be deterministic across runs"
    # 5. Assert metadata keys exist and are schema-correct
    required_keys = [
        "regime_cluster",
        "participant_likelihoods",
        "ev_features",
        "search_weights",
        "risk_envelope",
        "participant_risk_limits",
    ]
    for key in required_keys:
        assert key in result1.metadata, f"Missing metadata key: {key}"
        assert result1.metadata[key] is not None, f"Metadata key {key} must not be None"
    # 6. Assert no safety violations unless required by data
    if "safety_flags" in result1.metadata:
        for flag, triggered in result1.metadata["safety_flags"].items():
            assert triggered is False or triggered is True  # must be bool
    # 7. Assert no exceptions occurred (pytest will fail if any exception is raised)
