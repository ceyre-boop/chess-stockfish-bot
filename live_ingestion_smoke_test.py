"""
Live Ingestion Smoke Test
-------------------------
This script demonstrates the full engine pipeline operating in real time:

- Provider adapters (Polygon, Alpaca, MT5)
- Triple-feed router
- Evaluator
- Policy engine
- Deterministic engine loop (run_once)
- Logging of state transitions

This is not a trading script — it is a visibility tool to confirm that
the ingestion, evaluation, and policy layers are functioning end-to-end.
"""

import time
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

# --- Providers -------------------------------------------------------------

from providers.polygon_adapter import PolygonAdapter
from providers.alpaca_adapter import AlpacaAdapter
from providers.mt5_adapter import MT5Adapter

# --- Router ---------------------------------------------------------------

from engine.router import TripleFeedRouter

# --- Evaluator & Policy ---------------------------------------------------

from engine.causal_evaluator import CausalEvaluator
from engine.policy_engine import PolicyEngine

# --- Engine Loop ----------------------------------------------------------

from engine.engine_loop import run_once


def log_state(state):
    """Simple logger for smoke test output."""
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    decision = state["decision"]
    print(f"[{ts}] Decision: {decision}")


def main():
    print("=== Live Ingestion Smoke Test ===")

    # 1. Instantiate providers
    polygon = PolygonAdapter()
    alpaca = AlpacaAdapter()
    mt5 = MT5Adapter()

    providers = {
        "polygon": polygon,
        "alpaca": alpaca,
        "mt5": mt5,
    }

    # 2. Router
    router = TripleFeedRouter(providers)

    # 3. Evaluator + Policy
    evaluator = CausalEvaluator()
    policy = PolicyEngine()

    # 4. Engine state
    state = None

    print("Starting live loop... (Ctrl+C to stop)\n")

    while True:
        try:
            # Pull merged bars
            merged_bars = router.get_latest()

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
            print("\nStopping smoke test.")
            break


if __name__ == "__main__":
    main()
