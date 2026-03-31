"""
Audit script for trading-stockfish codebase
Tests imports and basic functionality of key modules
"""
import sys
import importlib
import traceback

def test_import(module_path, item_name=None):
    """Test importing a module or specific item from it"""
    try:
        parts = module_path.split('.')
        module = importlib.import_module(module_path)
        if item_name:
            obj = getattr(module, item_name)
            return True, f"OK: {module_path}.{item_name}"
        return True, f"OK: {module_path}"
    except Exception as e:
        return False, f"FAIL: {module_path}{'.' + item_name if item_name else ''} - {type(e).__name__}: {str(e)[:80]}"

# Test cases
tests = [
    # Core engine components
    ("engine.participants.participant_taxonomy", "ParticipantType"),
    ("engine.participants.participant_taxonomy", "ParticipantSignature"),
    ("engine.brain.ev_participant_adapter", "build_ev_features_with_participants"),
    ("engine.regime.regime_policy_builder", "synthesize_regime_policies"),
    ("engine.regime.regime_cluster_model", None),
    ("engine.regime.regime_performance", None),
    ("engine.risk.participant_risk_envelope", None),
    ("engine.risk.regime_risk_envelope", None),
    
    # State components
    ("state.state_builder", "build_state"),
    ("state.schema", None),
    ("session_regime", None),
    
    # Feature modules
    ("candle_pattern_features", None),
    ("ict_smc_features", None),
    ("liquidity_depth_features", None),
    ("momentum_features", None),
    ("orderflow_features", None),
    ("volume_profile_features", None),
    
    # Config
    ("config.feature_registry", None),
    
    # Utils
    ("utils.helpers", None),
    ("utils.validators", None),
]

print("=" * 70)
print("TRADING-STOCKFISH CODEBASE AUDIT")
print("=" * 70)

passed = 0
failed = 0
results = []

for module_path, item_name in tests:
    success, msg = test_import(module_path, item_name)
    results.append((success, msg))
    if success:
        passed += 1
    else:
        failed += 1

# Print results
print("\nRESULTS:")
print("-" * 70)
for success, msg in results:
    status = "[PASS]" if success else "[FAIL]"
    print(f"{status} {msg}")

print("-" * 70)
print(f"SUMMARY: {passed} passed, {failed} failed")
print("=" * 70)
