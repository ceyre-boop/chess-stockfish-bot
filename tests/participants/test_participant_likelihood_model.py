
import copy
from engine.participants.participant_likelihood_model import (
    classify_participants, ParticipantLikelihood)
from engine.participants.participant_taxonomy import ParticipantType
from engine.participants.participant_features import ParticipantFeatureVector


def make_features(
    orderflow_velocity: float = 1.0,
    sweep_intensity: float = 1.0,
    absorption_ratio: float = 1.0,
    spread_pressure: float = 0.0,
    liquidity_removal_rate: float = 1.0,
    volatility_reaction: float = 1.0,
    time_of_day_bias: str = "all_day",
    news_window_behavior: str = "none",
    metadata: dict = None,
    **kwargs
) -> ParticipantFeatureVector:
    return ParticipantFeatureVector(
        orderflow_velocity=orderflow_velocity,
        sweep_intensity=sweep_intensity,
        absorption_ratio=absorption_ratio,
        spread_pressure=spread_pressure,
        liquidity_removal_rate=liquidity_removal_rate,
        volatility_reaction=volatility_reaction,
        time_of_day_bias=time_of_day_bias,
        news_window_behavior=news_window_behavior,
        metadata=metadata or {},
        **kwargs
    )



def test_deterministic_classification():
    f = make_features(sweep_intensity=10.0)
    out1 = classify_participants(f)
    out2 = classify_participants(f)
    assert out1 == out2
    assert all(isinstance(x, ParticipantLikelihood) for x in out1)



def test_probabilities_sum_to_one():
    f = make_features(sweep_intensity=10.0, orderflow_velocity=5.0,
                     volatility_reaction=2.0)
    out = classify_participants(f)
    total = sum(x.probability for x in out)
    assert abs(total - 1.0) < 1e-8



def test_sweep_bot_influence():
    f = make_features(sweep_intensity=10.0)
    out = classify_participants(f)
    sweep = [x for x in out if x.type == ParticipantType.SWEEP_BOT][0]
    assert sweep.probability > 0.15
    assert sweep.evidence["high_sweep_intensity"] is True



def test_market_maker_influence():
    f = make_features(absorption_ratio=2.0, sweep_intensity=1.0)
    out = classify_participants(f)
    mm = [x for x in out if x.type == ParticipantType.MARKET_MAKER][0]
    assert mm.probability > 0.15
    assert mm.evidence["high_absorption_ratio"] is True
    assert mm.evidence["low_sweep_intensity"] is True



def test_news_algo_influence():
    f = make_features(news_window_behavior="during", volatility_reaction=2.0)
    out = classify_participants(f)
    news = [x for x in out if x.type == ParticipantType.NEWS_ALGO][0]
    assert news.probability > 0.15
    assert news.evidence["news_during_and_high_volatility"] is True



def test_evidence_schema():
    f = make_features()
    out = classify_participants(f)
    for x in out:
        assert isinstance(x.evidence, dict)



def test_stable_ordering():
    f = make_features()
    out = classify_participants(f)
    names = [x.type.name for x in out]
    assert names == sorted(names)



def test_no_mutation_of_input():
    f = make_features(sweep_intensity=10.0)
    f_copy = copy.deepcopy(f)
    classify_participants(f)
    assert f == f_copy
