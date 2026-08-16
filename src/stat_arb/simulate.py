"""Synthetic cointegrated pairs for demos and unit tests."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from stat_arb.fundamentals import FundamentalSnapshot

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class SimulatedPair:
    """Two price paths plus optional volume, volatility, and fundamentals."""

    prices_a: FloatArray
    prices_b: FloatArray
    volumes_a: FloatArray
    volumes_b: FloatArray
    spread: FloatArray
    fundamentals_a: FundamentalSnapshot
    fundamentals_b: FundamentalSnapshot
    true_beta: float
    true_half_life: float
    market_returns: FloatArray


def generate_cointegrated_pair(
    nobs: int = 756,
    beta: float = 1.25,
    kappa: float = np.log(2.0) / 10.0,
    sigma_spread: float = 0.018,
    mu_spread: float = 0.0,
    drift_b: float = 0.00015,
    sigma_b: float = 0.014,
    price0_a: float = 52.0,
    price0_b: float = 38.0,
    break_at: int | None = None,
    break_beta: float | None = None,
    seed: int = 7,
) -> SimulatedPair:
    """Simulate ``log P_A = α + β log P_B + S`` with an OU spread.

    After ``break_at`` the spread can stop mean-reverting and/or the hedge
    ratio can jump, which is the regime-break case the strategy should exit.
    """

    if nobs < 50:
        raise ValueError("nobs must be at least 50")
    rng = np.random.default_rng(seed)
    dt = 1.0
    log_b = np.empty(nobs, dtype=np.float64)
    log_b[0] = np.log(price0_b)
    shocks_b = rng.normal(drift_b, sigma_b, nobs - 1)
    log_b[1:] = log_b[0] + np.cumsum(shocks_b)

    spread = np.empty(nobs, dtype=np.float64)
    spread[0] = mu_spread
    ar = float(np.exp(-kappa * dt))
    ou_vol = float(sigma_spread * np.sqrt((1.0 - np.exp(-2.0 * kappa * dt)) / (2.0 * kappa)))
    current_beta = beta
    alpha = np.log(price0_a) - beta * np.log(price0_b)
    log_a = np.empty(nobs, dtype=np.float64)
    log_a[0] = alpha + beta * log_b[0] + spread[0]

    for t in range(1, nobs):
        if break_at is not None and t >= break_at:
            if t == break_at and break_beta is not None:
                current_beta = break_beta
            ar_t = 1.0
            ou_vol_t = sigma_spread
        else:
            ar_t = ar
            ou_vol_t = ou_vol
        spread[t] = mu_spread + ar_t * (spread[t - 1] - mu_spread) + ou_vol_t * rng.normal()
        log_a[t] = alpha + current_beta * log_b[t] + spread[t]

    prices_a = np.exp(log_a)
    prices_b = np.exp(log_b)
    ret_a = np.diff(log_a, prepend=log_a[0])
    ret_b = np.diff(log_b, prepend=log_b[0])
    volumes_a = rng.lognormal(mean=14.2, sigma=0.25, size=nobs) * (1.0 + 3.0 * np.abs(ret_a))
    volumes_b = rng.lognormal(mean=14.0, sigma=0.25, size=nobs) * (1.0 + 3.0 * np.abs(ret_b))
    market = 0.6 * ret_b + 0.4 * rng.normal(0.0001, 0.01, nobs)
    half_life = float(np.log(2.0) / kappa) if kappa > 0.0 else np.inf
    first = FundamentalSnapshot(
        ticker="AAA",
        industry="broker",
        roe=0.12,
        net_margin=0.28,
        ebitda_margin=0.35,
        revenue_growth=0.08,
        pe=12.5,
        pb=1.4,
        leverage=1.8,
        eps=price0_a / 12.5,
        adv=float(np.median(prices_a * volumes_a)),
        bid_ask_bps=4.0,
    )
    second = FundamentalSnapshot(
        ticker="BBB",
        industry="broker",
        roe=0.11,
        net_margin=0.26,
        ebitda_margin=0.33,
        revenue_growth=0.07,
        pe=13.0,
        pb=1.5,
        leverage=1.9,
        eps=price0_b / 13.0,
        adv=float(np.median(prices_b * volumes_b)),
        bid_ask_bps=5.0,
    )
    return SimulatedPair(
        prices_a=prices_a,
        prices_b=prices_b,
        volumes_a=volumes_a,
        volumes_b=volumes_b,
        spread=spread,
        fundamentals_a=first,
        fundamentals_b=second,
        true_beta=beta,
        true_half_life=half_life,
        market_returns=market,
    )


def generate_independent_pair(nobs: int = 756, seed: int = 11) -> SimulatedPair:
    """Two independent random walks that should fail cointegration screening."""

    rng = np.random.default_rng(seed)
    time = np.arange(nobs, dtype=np.float64)
    log_a = np.cumsum(rng.normal(0.0004, 0.02, nobs)) + 0.00003 * time
    log_b = np.cumsum(rng.normal(-0.0002, 0.011, nobs)) - 0.00001 * time**1.15
    prices_a = 40.0 * np.exp(log_a - log_a[0])
    prices_b = 55.0 * np.exp(log_b - log_b[0])
    volumes_a = rng.lognormal(14.0, 0.3, nobs)
    volumes_b = rng.lognormal(14.0, 0.3, nobs)
    first = FundamentalSnapshot(
        ticker="XXX",
        industry="airline",
        roe=0.05,
        net_margin=0.04,
        ebitda_margin=0.12,
        revenue_growth=0.03,
        pe=22.0,
        pb=1.1,
        leverage=2.4,
        eps=float(prices_a[0] / 22.0),
        adv=float(np.median(prices_a * volumes_a)),
        bid_ask_bps=8.0,
    )
    second = FundamentalSnapshot(
        ticker="YYY",
        industry="airline",
        roe=0.18,
        net_margin=0.15,
        ebitda_margin=0.22,
        revenue_growth=0.14,
        pe=9.0,
        pb=2.8,
        leverage=0.6,
        eps=float(prices_b[0] / 9.0),
        adv=float(np.median(prices_b * volumes_b)),
        bid_ask_bps=6.0,
    )
    dummy_spread = np.log(prices_a) - np.log(prices_b)
    market = rng.normal(0.0001, 0.01, nobs)
    return SimulatedPair(
        prices_a=prices_a,
        prices_b=prices_b,
        volumes_a=volumes_a,
        volumes_b=volumes_b,
        spread=dummy_spread,
        fundamentals_a=first,
        fundamentals_b=second,
        true_beta=np.nan,
        true_half_life=np.inf,
        market_returns=market,
    )
