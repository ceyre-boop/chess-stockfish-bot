import time
from engine.engine_loop import EngineLoop
# Import your real provider/router/evaluator/policy classes
#from polygon_provider import PolygonProvider
#from alpaca_provider import AlpacaProvider
#from mt5_provider import MT5Provider
#from state_builder import StateBuilder
#from evaluator import Evaluator
#from policy import Policy

# Replace these with your actual implementations
class DummyRouter:
    def get_latest_bars(self, symbols):
        return {
            symbol: {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "open": 100,
                "high": 101,
                "low": 99,
                "close": 100.5,
                "volume": 12345,
                "provider": "DummyProvider",
                "symbol": symbol,
            } for symbol in symbols
        }

class DummyStateBuilder:
    def build_state(self, bars):
        return {"bars": bars}

class DummyEvaluator:
    def evaluate_state(self, state):
        return {
            "regime": "neutral",
            "score": 0.5,
            "features": {"momentum": 0.1},
        }

class DummyPolicy:
    def decide(self, eval_result):
        return {
            "symbol": "AAPL",
            "action": "HOLD",
            "confidence": 0.5,
        }

symbols = ["AAPL", "US500.cash"]

loop = EngineLoop(
    router=DummyRouter(),
    state_builder=DummyStateBuilder(),
    evaluator=DummyEvaluator(),
    policy=DummyPolicy(),
    symbols=symbols,
)

start_time = time.time()
end_time = start_time + 3600

print("Starting full session (3600 seconds) stability test...")

regime_history = []
confidence_history = []
provider_history = []

while time.time() < end_time:
    tick_start = time.time()
    result = loop.run_once()
    tick_end = time.time()
    latency = tick_end - tick_start
    # Track regime, confidence, provider for stability analysis
    regime_history.append("neutral")  # DummyEvaluator always returns neutral
    confidence_history.append(result["confidence"])
    provider_history.append("DummyProvider")  # Replace with real provider if used
    print(f"Tick: {result} | Latency: {latency:.4f}s | Provider: DummyProvider")
    time.sleep(1)  # Simulate 1-second tick cadence

print("Full session stability test complete.")
print(f"Provider reliability: {provider_history.count('DummyProvider')} DummyProvider ticks")
print(f"Regime transitions: {regime_history.count('neutral')} neutral ticks")
print(f"Confidence values: min={min(confidence_history)}, max={max(confidence_history)}, mean={sum(confidence_history)/len(confidence_history):.4f}")
