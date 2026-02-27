from typing import Any, Callable

# 1. Type alias for state
State = dict  # placeholder for now

# 2. Engine loop function
def run_engine(bus, initial_state: State, reducer: Callable[[State, Any], State], max_events: int = 1000) -> State:
    """
    Consume up to max_events from bus, apply reducer, return final state.
    """
    state = initial_state
    for _ in range(max_events):
        event = bus.consume()
        state = reducer(state, event)
    return state
