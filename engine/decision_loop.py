# engine/decision_loop.py

from engine.engine_loop import run_once

def run_decision_loop(providers, evaluator, policy, steps=1, log_hook=None):
    """
    Deterministic multi-step decision loop used by functional tests.
    """
    state = None
    results = []

    for _ in range(steps):
        state = run_once(
            providers=providers,
            evaluator=evaluator,
            policy=policy,
            state=state,
            log_hook=log_hook,
        )
        results.append(state)

    return results
