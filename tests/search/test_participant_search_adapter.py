import copy
from engine.search.participant_search_adapter import get_participant_scoring_weights, ParticipantScoringWeights
from engine.participants.participant_likelihood_model import ParticipantLikelihood
from engine.participants.participant_taxonomy import ParticipantType

def make_likelihoods(**overrides):
    base = {
        ParticipantType.RETAIL: 0.1,
        ParticipantType.ALGO: 0.1,
        ParticipantType.MARKET_MAKER: 0.1,
        ParticipantType.FUND: 0.1,
        ParticipantType.NEWS_ALGO: 0.1,
        ParticipantType.LIQUIDITY_HUNTER: 0.1,
        ParticipantType.SWEEP_BOT: 0.1,
    }
    # Map string keys in overrides to ParticipantType
    for k, v in overrides.items():
        if isinstance(k, ParticipantType):
            base[k] = v
        else:
            try:
                pt = ParticipantType[k]
                base[pt] = v
            except Exception:
                raise ValueError(f"Unknown participant type: {k}")
    return [
        ParticipantLikelihood(type=ptype, probability=prob, evidence={})
        for ptype, prob in base.items()
    ]

def test_deterministic_weights():
    lik = make_likelihoods()
    w1 = get_participant_scoring_weights(lik)
    w2 = get_participant_scoring_weights(lik)
    assert w1 == w2
    assert isinstance(w1, ParticipantScoringWeights)

def test_sweep_bot_increases_tail_risk():
    lik = make_likelihoods(SWEEP_BOT=0.2)
    w = get_participant_scoring_weights(lik)
    assert w.tail_risk_weight > 1.0
    assert w.metadata['sweep_bot_tail_risk'] is True

def test_liquidity_hunter_increases_variance():
    lik = make_likelihoods(LIQUIDITY_HUNTER=0.2)
    w = get_participant_scoring_weights(lik)
    assert w.variance_weight > 1.0
    assert w.metadata['liquidity_hunter_variance'] is True

def test_market_maker_increases_mean_reversion():
    lik = make_likelihoods(MARKET_MAKER=0.2)
    w = get_participant_scoring_weights(lik)
    assert w.ev_weight < 1.0
    assert w.mcr_weight > 1.0
    assert w.metadata['market_maker_mean_reversion'] is True

def test_fund_increases_trend_continuation():
    lik = make_likelihoods(FUND=0.2)
    w = get_participant_scoring_weights(lik)
    assert w.ev_weight > 1.0
    assert w.metadata['fund_trend_continuation'] is True

def test_news_algo_shortens_horizon_and_increases_variance():
    lik = make_likelihoods(NEWS_ALGO=0.2)
    w = get_participant_scoring_weights(lik)
    assert w.rollout_horizon < 10
    assert w.variance_weight > 1.0
    assert w.metadata['news_algo_short_horizon'] is True

def test_retail_increases_path_count():
    lik = make_likelihoods(RETAIL=0.2)
    w = get_participant_scoring_weights(lik)
    assert w.path_count > 16
    assert w.metadata['retail_path_count'] is True

def test_metadata_schema():
    lik = make_likelihoods(SWEEP_BOT=0.2, FUND=0.2)
    w = get_participant_scoring_weights(lik)
    assert isinstance(w.metadata, dict)
    for k in [
        'sweep_bot_tail_risk', 'liquidity_hunter_variance', 'market_maker_mean_reversion',
        'fund_trend_continuation', 'news_algo_short_horizon', 'retail_path_count']:
        assert k in w.metadata

def test_no_mutation_of_input():
    lik = make_likelihoods(SWEEP_BOT=0.2)
    lik_copy = copy.deepcopy(lik)
    _ = get_participant_scoring_weights(lik)
    assert lik == lik_copy
