
import pytest
from unittest.mock import MagicMock
from engine.engine_loop import EngineLoop

class DummyState:
    def __init__(self):
        self.timestamp = "2026-02-06T00:00:00Z"
        self.symbols = ["AAPL", "US500.cash"]

@pytest.fixture
def mock_router():
    router = MagicMock()
    router.get_latest_bars.return_value = {
        "AAPL": {
            "timestamp": "2026-02-06T00:00:00Z",
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100.5,
            "volume": 12345,
            "provider": "MockProvider",
            "symbol": "AAPL",
        }
    }
    return router

@pytest.fixture
def mock_state_builder():
    sb = MagicMock()
    sb.build_state.return_value = DummyState()
    return sb

@pytest.fixture
def mock_evaluator():
    ev = MagicMock()
    ev.evaluate_state.return_value = {
        "regime": "neutral",
        "score": 0.5,
        "features": {"momentum": 0.1},
    }
    return ev

@pytest.fixture
def mock_policy():
    policy = MagicMock()
    policy.decide.return_value = {
        "symbol": "AAPL",
        "action": "HOLD",
        "confidence": 0.5,
    }
    return policy

def test_engine_loop_initialization(mock_router, mock_state_builder, mock_evaluator, mock_policy):
    loop = EngineLoop(
        router=mock_router,
        state_builder=mock_state_builder,
        evaluator=mock_evaluator,
        policy=mock_policy,
        symbols=["AAPL"],
    )
    assert loop is not None
    assert loop.symbols == ["AAPL"]

def test_engine_loop_run_once(mock_router, mock_state_builder, mock_evaluator, mock_policy):
    loop = EngineLoop(
        router=mock_router,
        state_builder=mock_state_builder,
        evaluator=mock_evaluator,
        policy=mock_policy,
        symbols=["AAPL"],
    )

    result = loop.run_once()

    assert isinstance(result, dict)
    assert "symbol" in result
    assert "action" in result
    assert "confidence" in result
    assert result["symbol"] == "AAPL"
