"""Fundamental similarity, distance, and relative-value fair ratios."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]

DEFAULT_DISTANCE_WEIGHTS: dict[str, float] = {
    "roe": 1.0,
    "net_margin": 1.0,
    "ebitda_margin": 1.0,
    "revenue_growth": 1.0,
    "pe": 0.5,
    "pb": 0.5,
    "leverage": 0.5,
}


@dataclass(frozen=True)
class FundamentalSnapshot:
    """Point-in-time fundamentals used to screen or value a pair.

    Args:
        ticker: Security identifier.
        industry: Industry or sector label used for hard screening.
        roe: Return on equity as a decimal, for example ``0.15``.
        net_margin: Net profit margin as a decimal.
        ebitda_margin: EBITDA margin as a decimal.
        revenue_growth: Year-over-year revenue growth as a decimal.
        pe: Price-to-earnings ratio.
        pb: Price-to-book ratio.
        leverage: Debt-to-equity or similar leverage ratio.
        eps: Trailing or forward earnings per share.
        adv: Average daily dollar volume.
        bid_ask_bps: Bid-ask spread in basis points.
    """

    ticker: str
    industry: str = ""
    roe: float = np.nan
    net_margin: float = np.nan
    ebitda_margin: float = np.nan
    revenue_growth: float = np.nan
    pe: float = np.nan
    pb: float = np.nan
    leverage: float = np.nan
    eps: float = np.nan
    adv: float = np.nan
    bid_ask_bps: float = np.nan


@dataclass(frozen=True)
class FairRatioCoef:
    """Linear mapping from fundamental ratios to a fair price ratio."""

    alpha: float = 0.0
    eps: float = 1.0
    roe: float = 0.0
    net_margin: float = 0.0


def _abs_diff(left: float, right: float) -> float:
    """Return an absolute gap, or NaN if either input is missing."""

    if not np.isfinite(left) or not np.isfinite(right):
        return np.nan
    return abs(float(left) - float(right))


def _safe_ratio(left: float, right: float) -> float:
    """Return ``left / right`` when both values are usable."""

    if not np.isfinite(left) or not np.isfinite(right) or right == 0.0:
        return np.nan
    return float(left) / float(right)


def fundamental_distance(
    first: FundamentalSnapshot,
    second: FundamentalSnapshot,
    weights: dict[str, float] | None = None,
) -> float:
    """Weighted L1 distance between two fundamental snapshots.

    Only features that are finite on both names contribute. The result is
    the weighted mean of those absolute gaps, so missing fields do not
    automatically reject a pair.
    """

    chosen = DEFAULT_DISTANCE_WEIGHTS if weights is None else weights
    gaps = {
        "roe": _abs_diff(first.roe, second.roe),
        "net_margin": _abs_diff(first.net_margin, second.net_margin),
        "ebitda_margin": _abs_diff(first.ebitda_margin, second.ebitda_margin),
        "revenue_growth": _abs_diff(first.revenue_growth, second.revenue_growth),
        "pe": _abs_diff(first.pe, second.pe),
        "pb": _abs_diff(first.pb, second.pb),
        "leverage": _abs_diff(first.leverage, second.leverage),
    }
    weighted: list[float] = []
    total_weight = 0.0
    for name, gap in gaps.items():
        weight = float(chosen.get(name, 0.0))
        if weight <= 0.0 or not np.isfinite(gap):
            continue
        weighted.append(weight * gap)
        total_weight += weight
    if total_weight <= 0.0:
        return np.nan
    return float(np.sum(weighted) / total_weight)


def same_industry(first: FundamentalSnapshot, second: FundamentalSnapshot) -> bool:
    """Return whether both names have a matching non-empty industry label."""

    if not first.industry or not second.industry:
        return False
    return first.industry.strip().lower() == second.industry.strip().lower()


def naive_fair_price_ratio(first: FundamentalSnapshot, second: FundamentalSnapshot) -> float:
    """Heuristic fair ``P_A / P_B`` from current fundamentals.

    When earnings are available the ratio of EPS is the PE-parity value.
    ROE and margin ratios are blended in when present so the fair value
    is not a pure earnings multiple.
    """

    parts = [
        _safe_ratio(first.eps, second.eps),
        _safe_ratio(first.roe, second.roe),
        _safe_ratio(first.net_margin, second.net_margin),
    ]
    finite = [part for part in parts if np.isfinite(part) and part > 0.0]
    if not finite:
        return np.nan
    return float(np.mean(finite))


def fair_price_ratio(
    first: FundamentalSnapshot,
    second: FundamentalSnapshot,
    coef: FairRatioCoef | None = None,
) -> float:
    """Model-based fair price ratio ``α + β·(fundamental ratios)``."""

    chosen = FairRatioCoef() if coef is None else coef
    eps_ratio = _safe_ratio(first.eps, second.eps)
    roe_ratio = _safe_ratio(first.roe, second.roe)
    margin_ratio = _safe_ratio(first.net_margin, second.net_margin)
    value = chosen.alpha
    used = False
    if np.isfinite(eps_ratio):
        value += chosen.eps * eps_ratio
        used = True
    if np.isfinite(roe_ratio):
        value += chosen.roe * roe_ratio
        used = True
    if np.isfinite(margin_ratio):
        value += chosen.net_margin * margin_ratio
        used = True
    if not used:
        return np.nan
    return float(value)


def relative_value_mispricing(
    price_a: float,
    price_b: float,
    first: FundamentalSnapshot,
    second: FundamentalSnapshot,
    coef: FairRatioCoef | None = None,
) -> float:
    """``ActualRatio - FairRatio`` for the current prices and fundamentals."""

    if price_b == 0.0 or not np.isfinite(price_a) or not np.isfinite(price_b):
        return np.nan
    fair = fair_price_ratio(first, second, coef=coef)
    if not np.isfinite(fair):
        fair = naive_fair_price_ratio(first, second)
    if not np.isfinite(fair):
        return np.nan
    return float(price_a / price_b - fair)


def estimate_fair_ratio_coefs(
    price_ratio: FloatArray,
    eps_ratio: FloatArray,
    roe_ratio: FloatArray,
    margin_ratio: FloatArray,
) -> FairRatioCoef:
    """OLS of the observed price ratio on contemporaneous fundamental ratios."""

    from stat_arb.spread import ols

    dependent = np.asarray(price_ratio, dtype=np.float64)
    columns = np.column_stack(
        [
            np.asarray(eps_ratio, dtype=np.float64),
            np.asarray(roe_ratio, dtype=np.float64),
            np.asarray(margin_ratio, dtype=np.float64),
        ]
    )
    mask = np.isfinite(dependent) & np.all(np.isfinite(columns), axis=1)
    if int(np.count_nonzero(mask)) < 5:
        raise ValueError("need at least 5 complete observations to estimate fair-ratio coefficients")
    fitted = ols(dependent[mask], columns[mask], add_const=True)
    beta = fitted.beta
    return FairRatioCoef(alpha=float(beta[0]), eps=float(beta[1]), roe=float(beta[2]), net_margin=float(beta[3]))


def candidate_pairs(
    snapshots: list[FundamentalSnapshot],
    max_distance: float,
    require_same_industry: bool = True,
    weights: dict[str, float] | None = None,
) -> list[tuple[FundamentalSnapshot, FundamentalSnapshot, float]]:
    """Return industry-filtered pairs whose fundamental distance is below a cutoff."""

    ranked: list[tuple[FundamentalSnapshot, FundamentalSnapshot, float]] = []
    for i, first in enumerate(snapshots):
        for second in snapshots[i + 1 :]:
            if require_same_industry and not same_industry(first, second):
                continue
            distance = fundamental_distance(first, second, weights=weights)
            if np.isfinite(distance) and distance < max_distance:
                ranked.append((first, second, float(distance)))
    ranked.sort(key=lambda item: item[2])
    return ranked
