def run_once(providers, evaluator, policy, state=None, log_hook=None):
    """
    Single deterministic engine step.
    Pulls data from providers, evaluates, applies policy, returns new state.
    """
    bars = {}
    for name, provider in providers.items():
        bars[name] = provider.get_latest_bar()

    eval_result = evaluator.evaluate(bars, state)
    decision = policy.decide(eval_result, state)

    new_state = {
        "bars": bars,
        "eval": eval_result,
        "decision": decision,
    }

    if log_hook:
        log_hook(new_state)

    return new_state

class EngineLoop:
    def __init__(self, router=None, state_builder=None, evaluator=None, policy=None, symbols=None, **kwargs):
        self.router = router
        self.state_builder = state_builder
        self.evaluator = evaluator
        self.policy = policy
        self.symbols = symbols or []
        self.state = None

    def run_once(self):
        # 1. Get latest bars from router
        bars = self.router.get_latest_bars(self.symbols)

        # 2. Build state
        state = self.state_builder.build_state(bars)

        # 3. Evaluate state
        eval_result = self.evaluator.evaluate_state(state)

        # 4. Decide action
        action = self.policy.decide(eval_result)

        # 5. Return action dict (normalized)
        return {
            "symbol": action["symbol"],
            "action": action["action"],
            "confidence": action["confidence"]
        }
