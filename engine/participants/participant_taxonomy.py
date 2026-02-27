from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict


class ParticipantType(Enum):
    RETAIL = "RETAIL"
    ALGO = "ALGO"
    MARKET_MAKER = "MARKET_MAKER"
    FUND = "FUND"
    NEWS_ALGO = "NEWS_ALGO"
    LIQUIDITY_HUNTER = "LIQUIDITY_HUNTER"
    SWEEP_BOT = "SWEEP_BOT"


@dataclass(frozen=True)
class ParticipantSignature:
    type: ParticipantType
    speed: str
    size_profile: str
    sweep_frequency: str
    absorption_behavior: str
    time_of_day_bias: str
    volatility_sensitivity: str
    metadata: Dict[str, Any]


def _sig(
    ptype: ParticipantType,
    *,
    speed: str,
    size_profile: str,
    sweep_frequency: str,
    absorption_behavior: str,
    time_of_day_bias: str,
    volatility_sensitivity: str,
    metadata: Dict[str, Any] | None = None,
) -> ParticipantSignature:
    return ParticipantSignature(
        type=ptype,
        speed=speed,
        size_profile=size_profile,
        sweep_frequency=sweep_frequency,
        absorption_behavior=absorption_behavior,
        time_of_day_bias=time_of_day_bias,
        volatility_sensitivity=volatility_sensitivity,
        metadata=metadata or {},
    )


def get_participant_signatures() -> Dict[ParticipantType, ParticipantSignature]:
    # Deterministic, hard-coded taxonomy consistent with intuitive behaviors
    return {
        ParticipantType.RETAIL: _sig(
            ParticipantType.RETAIL,
            speed="slow",
            size_profile="small_clip",
            sweep_frequency="rare",
            absorption_behavior="hits_liquidity",
            time_of_day_bias="all_day",
            volatility_sensitivity="avoids_vol",
            metadata={"description": "Discretionary/retail flow; smaller clips; avoids volatility"},
        ),
        ParticipantType.ALGO: _sig(
            ParticipantType.ALGO,
            speed="fast",
            size_profile="mid_clip",
            sweep_frequency="occasional",
            absorption_behavior="hits_liquidity",
            time_of_day_bias="all_day",
            volatility_sensitivity="neutral",
            metadata={"description": "Generic execution algos; balanced speed and size"},
        ),
        ParticipantType.MARKET_MAKER: _sig(
            ParticipantType.MARKET_MAKER,
            speed="fast",
            size_profile="small_clip",
            sweep_frequency="frequent",
            absorption_behavior="provides_liquidity",
            time_of_day_bias="all_day",
            volatility_sensitivity="avoids_vol",
            metadata={"description": "Quotes both sides, provides liquidity, throttles in high vol"},
        ),
        ParticipantType.FUND: _sig(
            ParticipantType.FUND,
            speed="medium",
            size_profile="block",
            sweep_frequency="rare",
            absorption_behavior="hits_liquidity",
            time_of_day_bias="mid",
            volatility_sensitivity="neutral",
            metadata={"description": "Larger portfolio rebalances; mid-day bias; block trades"},
        ),
        ParticipantType.NEWS_ALGO: _sig(
            ParticipantType.NEWS_ALGO,
            speed="ultra_fast",
            size_profile="mid_clip",
            sweep_frequency="burst",
            absorption_behavior="hits_liquidity",
            time_of_day_bias="all_day",
            volatility_sensitivity="seeks_vol",
            metadata={"description": "News-reactive; ultra fast bursts around events"},
        ),
        ParticipantType.LIQUIDITY_HUNTER: _sig(
            ParticipantType.LIQUIDITY_HUNTER,
            speed="fast",
            size_profile="mid_clip",
            sweep_frequency="frequent",
            absorption_behavior="pulls_liquidity",
            time_of_day_bias="open",
            volatility_sensitivity="seeks_vol",
            metadata={"description": "Seeks hidden/large liquidity; aggressive when available"},
        ),
        ParticipantType.SWEEP_BOT: _sig(
            ParticipantType.SWEEP_BOT,
            speed="fast",
            size_profile="sweep",
            sweep_frequency="burst",
            absorption_behavior="hits_liquidity",
            time_of_day_bias="close",
            volatility_sensitivity="seeks_vol",
            metadata={"description": "Executes rapid sweeps across venues; close/volatility oriented"},
        ),
    }
