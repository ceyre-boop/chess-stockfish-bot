from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from engine.regime.regime_cluster_model import RegimeCluster


@dataclass(frozen=True)
class RegimeScoringWeights:
    lambda_ev: float
    lambda_mcr: float
    lambda_variance: float
    lambda_tail_risk: float
    lambda_policy_boost: float
    rollout_horizon: int
    mc_paths: int
    opening_book_weight: float


def get_regime_scoring_weights(cluster: RegimeCluster) -> RegimeScoringWeights:
    """
    Deterministic mapping of regime cluster to scoring weights.
    """

    # Base defaults align with prior unified scoring constants.
    base = RegimeScoringWeights(
        lambda_ev=1.0,
        lambda_mcr=0.5,
        lambda_variance=0.2,
        lambda_tail_risk=0.3,
        lambda_policy_boost=1.0,
        rollout_horizon=60,
        mc_paths=64,
        opening_book_weight=1.0,
    )

    overrides: Dict[RegimeCluster, Dict[str, float | int]] = {
        RegimeCluster.NEWS_SHOCK_EXPLOSION: {
            "lambda_variance": 0.5,
            "lambda_tail_risk": 0.7,
            "lambda_mcr": 0.4,
            "rollout_horizon": 20,
            "mc_paths": 24,
            "opening_book_weight": 0.5,
        },
        RegimeCluster.NEWS_PRE_RELEASE_COMPRESSION: {
            "lambda_variance": 0.35,
            "lambda_tail_risk": 0.5,
            "lambda_mcr": 0.4,
            "rollout_horizon": 30,
            "mc_paths": 32,
            "opening_book_weight": 0.3,
        },
        RegimeCluster.NEWS_POST_DIGESTION_TREND: {
            "lambda_variance": 0.2,
            "lambda_tail_risk": 0.25,
            "lambda_mcr": 0.55,
            "rollout_horizon": 50,
            "mc_paths": 80,
            "opening_book_weight": 1.2,
        },
        RegimeCluster.VOLATILITY_BREAKOUT: {
            "lambda_variance": 0.35,
            "lambda_tail_risk": 0.4,
            "rollout_horizon": 45,
            "mc_paths": 48,
        },
        RegimeCluster.CHOPPY_MANIPULATION: {
            "lambda_variance": 0.3,
            "lambda_tail_risk": 0.35,
            "rollout_horizon": 40,
            "mc_paths": 40,
        },
        RegimeCluster.LIQUIDITY_DRAIN: {
            "lambda_variance": 0.25,
            "lambda_tail_risk": 0.3,
            "lambda_mcr": 0.45,
            "rollout_horizon": 40,
            "mc_paths": 48,
            "opening_book_weight": 0.8,
        },
    }

    if cluster in overrides:
        ov = overrides[cluster]
        return RegimeScoringWeights(
            lambda_ev=ov.get("lambda_ev", base.lambda_ev),
            lambda_mcr=ov.get("lambda_mcr", base.lambda_mcr),
            lambda_variance=ov.get("lambda_variance", base.lambda_variance),
            lambda_tail_risk=ov.get("lambda_tail_risk", base.lambda_tail_risk),
            lambda_policy_boost=ov.get("lambda_policy_boost", base.lambda_policy_boost),
            rollout_horizon=int(ov.get("rollout_horizon", base.rollout_horizon)),
            mc_paths=int(ov.get("mc_paths", base.mc_paths)),
            opening_book_weight=float(
                ov.get("opening_book_weight", base.opening_book_weight)
            ),
        )

    return base
