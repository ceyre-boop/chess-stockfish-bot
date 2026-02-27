import pytest

from engine import search_scoring
from engine.decision_actions import ActionType, DecisionAction
from engine.decision_frame import DecisionFrame
from engine.regime.regime_cluster_model import RegimeCluster
from engine.search.search_engine_regime_adapter import get_regime_scoring_weights


class _BrainPolicy:
    def lookup(self, entry_id, frame):
        return "ALLOWED"

    def multiplier_for(self, label):
        return 0.0


class _DummyEVBrain:
    def predict(self, X):
        import numpy as np

        return np.ones(len(X)) * 0.5


def _actions():
    return [
        DecisionAction(
            action_type=ActionType.OPEN_LONG,
            entry_model_id="A",
            template_id="T_A",
        ),
        DecisionAction(
            action_type=ActionType.OPEN_LONG,
            entry_model_id="B",
            template_id="T_B",
        ),
        DecisionAction(
            action_type=ActionType.OPEN_LONG,
            entry_model_id="C",
            template_id="T_C",
        ),
    ]


def _rank(scored):
    return [
        a.entry_model_id
        for a, _ in sorted(
            scored,
            key=lambda x: (-x[1]["unified_score"], x[0].entry_model_id),
        )
    ]


@pytest.fixture(autouse=True)
def deterministic_scoring(monkeypatch):
    def fake_ev_brain_score(ev_brain, frame, action):
        mapping = {"A": 0.55, "B": 0.65, "C": 0.6}
        return mapping.get(action.entry_model_id, 0.5)

    def fake_mcr(frame, ctx, n_paths, horizon_bars, seed):
        entry = ctx.decision_action.entry_model_id
        if entry == "A":
            return {
                "mean_EV": 1.1,
                "variance_EV": 0.2,
                "tail_risk": 0.1,
                "tp_hit_rate": 0.0,
                "stop_hit_rate": 0.0,
            }
        if entry == "B":
            return {
                "mean_EV": 1.5,
                "variance_EV": 0.7,
                "tail_risk": 0.6,
                "tp_hit_rate": 0.0,
                "stop_hit_rate": 0.0,
            }
        return {
            "mean_EV": 0.9,
            "variance_EV": 0.3,
            "tail_risk": 0.2,
            "tp_hit_rate": 0.0,
            "stop_hit_rate": 0.0,
        }

    monkeypatch.setattr(search_scoring, "_ev_brain_score", fake_ev_brain_score)
    monkeypatch.setattr(search_scoring, "evaluate_action_via_mcr", fake_mcr)


def test_scoring_weights_change_by_regime():
    base = get_regime_scoring_weights(RegimeCluster.EXPANSIVE_TREND)
    shock = get_regime_scoring_weights(RegimeCluster.NEWS_SHOCK_EXPLOSION)
    pre = get_regime_scoring_weights(RegimeCluster.NEWS_PRE_RELEASE_COMPRESSION)
    post = get_regime_scoring_weights(RegimeCluster.NEWS_POST_DIGESTION_TREND)

    assert shock.lambda_variance > base.lambda_variance
    assert shock.rollout_horizon < base.rollout_horizon
    assert pre.rollout_horizon < base.rollout_horizon
    assert post.mc_paths > base.mc_paths
    assert post.opening_book_weight >= base.opening_book_weight

    for weights in [base, shock, pre, post]:
        assert weights.rollout_horizon > 0
        assert weights.mc_paths > 0
        assert weights.rollout_horizon <= 120
        assert weights.mc_paths <= 128

    # deterministic mapping
    assert get_regime_scoring_weights(RegimeCluster.EXPANSIVE_TREND) == base


def test_news_shock_increases_variance_weight():
    shock = get_regime_scoring_weights(RegimeCluster.NEWS_SHOCK_EXPLOSION)
    pre = get_regime_scoring_weights(RegimeCluster.NEWS_PRE_RELEASE_COMPRESSION)

    assert shock.lambda_variance > pre.lambda_variance
    assert shock.lambda_tail_risk >= pre.lambda_tail_risk


def test_pre_release_shortens_horizon():
    base = get_regime_scoring_weights(RegimeCluster.EXPANSIVE_TREND)
    pre = get_regime_scoring_weights(RegimeCluster.NEWS_PRE_RELEASE_COMPRESSION)

    assert pre.rollout_horizon < base.rollout_horizon
    assert pre.mc_paths <= base.mc_paths


def test_post_digest_increases_path_count():
    base = get_regime_scoring_weights(RegimeCluster.EXPANSIVE_TREND)
    post = get_regime_scoring_weights(RegimeCluster.NEWS_POST_DIGESTION_TREND)

    assert post.mc_paths > base.mc_paths
    assert post.rollout_horizon <= base.rollout_horizon


def test_search_ranking_changes_by_regime():
    frame = DecisionFrame(symbol="EURUSD")
    actions = _actions()
    kwargs = {
        "frame": frame,
        "position_state": {},
        "candidate_actions": actions,
        "ev_brain": _DummyEVBrain(),
        "brain_policy": _BrainPolicy(),
        "risk_envelope": {},
        "n_paths": 20,
        "horizon_bars": 30,
        "seed": 7,
        "template_policy": None,
    }

    post = get_regime_scoring_weights(RegimeCluster.NEWS_POST_DIGESTION_TREND)
    shock = get_regime_scoring_weights(RegimeCluster.NEWS_SHOCK_EXPLOSION)

    ranked_post = _rank(
        search_scoring.score_actions_via_search(**kwargs, regime_weights=post)
    )
    ranked_shock = _rank(
        search_scoring.score_actions_via_search(**kwargs, regime_weights=shock)
    )

    assert ranked_post[0] == "B"
    assert ranked_shock[0] == "A"  # variance/tail penalties flip the ordering
    assert ranked_post != ranked_shock


def test_regime_modulation_deterministic():
    frame = DecisionFrame(symbol="AAPL")
    actions = _actions()
    weights = get_regime_scoring_weights(RegimeCluster.CHOPPY_MANIPULATION)

    kwargs = {
        "frame": frame,
        "position_state": {"pos": 1},
        "candidate_actions": actions,
        "ev_brain": _DummyEVBrain(),
        "brain_policy": _BrainPolicy(),
        "risk_envelope": {"max_R": 1.0},
        "n_paths": 16,
        "horizon_bars": 24,
        "seed": 11,
        "regime_weights": weights,
        "template_policy": None,
    }

    first = search_scoring.score_actions_via_search(**kwargs)
    second = search_scoring.score_actions_via_search(**kwargs)

    assert first == second
    assert _rank(first) == ["A", "B", "C"]
