"""
Real-Time Live Smoke Test
-------------------------
Runs the full engine pipeline on real data for 60–300 seconds.

- Provider adapters (Polygon, Alpaca, MT5)
- Triple-feed router
- Causal evaluator
- Policy engine (regime/scenario/risk aware)
- Deterministic engine loop (run_once)
- Logs: symbol, regime, action, confidence, provider source
"""

import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Providers
from providers.polygon_adapter import PolygonAdapter
from providers.alpaca_adapter import AlpacaAdapter
from providers.mt5_adapter import MT5Adapter

# Router
from engine.router import TripleFeedRouter

# Evaluator + Policy
from engine.causal_evaluator import CausalEvaluator
from engine.policy_engine import PolicyEngine

# Engine loop
from engine.engine_loop import run_once


def log_state(state):
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    decision = state["decision"]
    eval_result = state["eval"]
    bars = state["bars"]

    # Extract metadata
    symbol = eval_result.get("symbol", "UNKNOWN")
    regime = eval_result.get("regime", "UNKNOWN")
    confidence = eval_result.get("confidence", 0.0)
    provider_used = eval_result.get("provider", "UNKNOWN")

    print(
        f"[{ts}] "
        f"symbol={symbol} "
        f"regime={regime} "
        f"action={decision} "
        f"confidence={confidence:.3f} "
        f"provider={provider_used}"
    )


def main():
    print("=== Real-Time Live Smoke Test ===")
    print("Running for ~120 seconds...\n")

    # Providers
    providers = {
        "polygon": PolygonAdapter(),
        "alpaca": AlpacaAdapter(),
        "mt5": MT5Adapter(),
    }

    # Router
    router = TripleFeedRouter(providers)

    # Evaluator + Policy
    evaluator = CausalEvaluator()
    policy = PolicyEngine()

    state = None
    start = time.time()

    while time.time() - start < 120:  # ~2 minutes
        try:
            # Pull merged bars
            merged = router.get_latest()

            # Run one deterministic engine step
            state = run_once(
                providers=providers,
                evaluator=evaluator,
                policy=policy,
                state=state,
                log_hook=log_state,
            )

            time.sleep(1)

        except KeyboardInterrupt:
            print("\nStopping early.")
            break

    print("\n=== Smoke Test Complete ===")


if __name__ == "__main__":
    main()
