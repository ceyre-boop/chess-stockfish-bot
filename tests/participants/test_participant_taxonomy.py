from engine.participants.participant_taxonomy import (
    ParticipantSignature, ParticipantType, get_participant_signatures)


def test_all_participant_types_present():
    sigs = get_participant_signatures()
    assert set(sigs.keys()) == set(ParticipantType)


def test_signatures_are_deterministic_and_non_empty():
    first = get_participant_signatures()
    second = get_participant_signatures()
    assert first == second

    for ptype, sig in first.items():
        assert isinstance(sig, ParticipantSignature)
        assert sig.type == ptype
        assert sig.speed
        assert sig.size_profile
        assert sig.sweep_frequency
        assert sig.absorption_behavior
        assert sig.time_of_day_bias
        assert sig.volatility_sensitivity
        assert isinstance(sig.metadata, dict)


def test_semantics_align_with_types():
    sigs = get_participant_signatures()

    mm = sigs[ParticipantType.MARKET_MAKER]
    assert mm.absorption_behavior == "provides_liquidity"
    assert mm.speed in {"fast", "ultra_fast"}

    retail = sigs[ParticipantType.RETAIL]
    assert retail.size_profile == "small_clip"
    assert retail.speed == "slow"

    news = sigs[ParticipantType.NEWS_ALGO]
    assert news.speed == "ultra_fast"
    assert news.volatility_sensitivity == "seeks_vol"
    assert news.sweep_frequency == "burst"

    sweep = sigs[ParticipantType.SWEEP_BOT]
    assert sweep.size_profile == "sweep"
    assert sweep.sweep_frequency in {"burst", "frequent"}

    hunter = sigs[ParticipantType.LIQUIDITY_HUNTER]
    assert hunter.absorption_behavior in {"pulls_liquidity", "hits_liquidity"}
    assert hunter.volatility_sensitivity == "seeks_vol"
