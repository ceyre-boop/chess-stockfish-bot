# ============================
# prove_system_online.ps1
# ============================

# Ensure we are in the project root
Set-Location $PSScriptRoot

# Activate venv
& "$PSScriptRoot\.venv\Scripts\Activate.ps1"

# Create Python proof script
$py = @"
from dotenv import load_dotenv
load_dotenv()

print("\n=== PROVIDER PROOF ===")

from providers.polygon_adapter import PolygonAdapter
from providers.alpaca_adapter import AlpacaAdapter
from providers.mt5_adapter import MT5Adapter

polygon = PolygonAdapter()
alpaca = AlpacaAdapter()
mt5 = MT5Adapter()

print("\nPolygon latest bar:")
print(polygon.get_latest_bar())

print("\nAlpaca latest bar:")
print(alpaca.get_latest_bar())

print("\nMT5 latest bar (XAUUSD):")
print(mt5.get_latest_bar("XAUUSD"))

print("\nMT5 latest bar (XAGUSD):")
print(mt5.get_latest_bar("XAGUSD"))

print("\n=== ROUTER PROOF ===")

from engine.router import TripleFeedRouter
providers = {"polygon": polygon, "alpaca": alpaca, "mt5": mt5}
router = TripleFeedRouter(providers)

merged = router.get_latest()
print("\nMerged router bar:")
print(merged)

print("\n=== EVALUATOR PROOF ===")

from engine.causal_evaluator import CausalEvaluator
evaluator = CausalEvaluator()

eval1 = evaluator.evaluate(merged, None)
eval2 = evaluator.evaluate(merged, None)

print("\nEvaluator output:")
print(eval1)

print("\nDeterministic check:", eval1 == eval2)

print("\n=== POLICY PROOF ===")

from engine.policy_engine import PolicyEngine
policy = PolicyEngine()

decision = policy.decide(eval1, None)
print("\nPolicy decision:")
print(decision)

print("\n=== ENGINE LOOP PROOF ===")

from engine.engine_loop import run_once

state = None
for i in range(3):
    state = run_once(
        providers=providers,
        evaluator=evaluator,
        policy=policy,
        state=state,
        log_hook=lambda s, i=i: print(f"Tick {i} decision:", s["decision"])
    )

print("\n=== END OF PROOF ===")
"@

# Write Python script to disk
$py | Out-File -FilePath "$PSScriptRoot\prove_system_online.py" -Encoding utf8

# Run it
python "$PSScriptRoot\prove_system_online.py"
