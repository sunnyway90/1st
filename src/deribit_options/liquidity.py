"""Option liquidity features and no-tick fill estimates.

These helpers are meant for patient, small-size limit orders on sparse option
books. They never treat mark or mid prices as executable, and they never set a
limit from the same bar's high/low (that would look ahead to the day's extreme).
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from statistics import median
from typing import Iterable, Literal, Sequence

from deribit_options.core import DeribitOptionQuote, OhlcBar


Side = Literal["buy", "sell"]
LiquidityBucket = Literal["liquid", "tradable_passive", "fragile", "unusable"]
PlausibilityVerdict = Literal[
    "plausible_if_patient",
    "fragile",
    "spread_dominates",
    "no_capacity",
    "untradable",
]


@dataclass(frozen=True)
class OptionLiquidityFeatures:
    """Liquidity snapshot for one option quote."""

    instrument_name: str
    two_sided: bool
    abs_spread: float | None
    relative_spread: float | None
    iv_spread: float | None
    volume: float | None
    volume_usd: float | None
    open_interest: float | None
    turnover: float | None
    range_pct: float | None
    last_inside_nbbo: bool | None
    zero_volume: bool
    stub_quote: bool
    liquidity_score: float
    bucket: LiquidityBucket
    flags: tuple[str, ...]


@dataclass(frozen=True)
class ChainLiquiditySummary:
    """Cross-sectional liquidity picture of one option-chain snapshot."""

    snapshot_time: datetime
    contract_count: int
    two_sided_count: int
    zero_volume_count: int
    median_relative_spread: float | None
    p90_relative_spread: float | None
    median_iv_spread: float | None
    contracts_with_volume_ge_size: int
    bucket_counts: dict[str, int]


@dataclass(frozen=True)
class PassiveFillEvent:
    """One estimated fill of a predetermined resting limit."""

    timestamp: datetime
    fill_price: float
    fill_size: float
    bar_open: float | None
    bar_close: float | None
    bar_volume: float | None
    mtm_vs_fill: float
    adverse_selection: float
    panic: bool


@dataclass(frozen=True)
class RestingFillResult:
    """Fill-rate and adverse-selection summary for a resting limit."""

    side: Side
    limit_price: float
    requested_size: float
    filled: bool
    fill_size: float
    fill_rate: float
    events: tuple[PassiveFillEvent, ...]
    median_adverse_selection: float | None
    mean_mtm_vs_fill: float | None
    participation_used: float


@dataclass(frozen=True)
class StrategyPlausibility:
    """Conservative check of whether a patient option trade is even tradable."""

    instrument_name: str
    side: Side
    size: float
    limit_price: float | None
    liquidity: OptionLiquidityFeatures
    half_spread_cost: float | None
    size_as_pct_of_volume: float | None
    fill_result: RestingFillResult | None
    required_edge: float | None
    verdict: PlausibilityVerdict
    notes: tuple[str, ...]


def mid_price(quote: DeribitOptionQuote) -> float | None:
    """Return a quote mid, falling back to the average of bid and ask."""

    if quote.mid_price is not None:
        return quote.mid_price
    if quote.bid_price is not None and quote.ask_price is not None:
        return (quote.bid_price + quote.ask_price) / 2.0
    return quote.mark_price


def relative_spread(quote: DeribitOptionQuote) -> float | None:
    """Return (ask - bid) / mid. Wide values mean the premium itself is noisy."""

    if quote.bid_price is None or quote.ask_price is None:
        return None
    center = mid_price(quote)
    if center is None or center <= 0:
        return None
    return (quote.ask_price - quote.bid_price) / center


def estimate_iv_spread(quote: DeribitOptionQuote, *, as_of: date | None = None) -> float | None:
    """Convert the price spread into implied-vol points using Black-76 vega.

    Deribit quotes BTC options as a coin fraction of the forward. Vega is
    therefore ``n(d1) * sqrt(T)`` coin per 1.00 volatility. A huge IV spread
    means the bid/ask is economically meaningless even if the raw price looks
    small.
    """

    if quote.bid_price is None or quote.ask_price is None:
        return None
    vega = _coin_vega_per_vol_point(quote, as_of=as_of)
    if vega is None or vega <= 1e-12:
        return None
    return (quote.ask_price - quote.bid_price) / vega


def liquidity_features(
    quote: DeribitOptionQuote,
    *,
    as_of: date | None = None,
    size: float = 0.1,
) -> OptionLiquidityFeatures:
    """Score one option quote without needing tick data."""

    abs_spread = None
    if quote.bid_price is not None and quote.ask_price is not None:
        abs_spread = quote.ask_price - quote.bid_price

    rel = relative_spread(quote)
    iv_spread = estimate_iv_spread(quote, as_of=as_of)
    two_sided = quote.bid_price is not None and quote.ask_price is not None
    volume = quote.volume if quote.volume is not None else 0.0
    zero_volume = volume <= 0
    turnover = None
    if quote.open_interest and quote.open_interest > 0 and quote.volume is not None:
        turnover = quote.volume / quote.open_interest

    center = mid_price(quote)
    range_pct = None
    if quote.high_price is not None and quote.low_price is not None and center and center > 0:
        range_pct = (quote.high_price - quote.low_price) / center

    last_inside = None
    if quote.last_price is not None and quote.bid_price is not None and quote.ask_price is not None:
        last_inside = quote.bid_price <= quote.last_price <= quote.ask_price

    stub_quote = (not two_sided) or (rel is not None and rel >= 0.5)
    flags = _liquidity_flags(
        two_sided=two_sided,
        rel=rel,
        iv_spread=iv_spread,
        volume=volume,
        open_interest=quote.open_interest,
        last_inside=last_inside,
        stub_quote=stub_quote,
        size=size,
    )
    score = _liquidity_score(
        two_sided=two_sided,
        rel=rel,
        volume=volume,
        open_interest=quote.open_interest,
        stub_quote=stub_quote,
    )
    return OptionLiquidityFeatures(
        instrument_name=quote.instrument_name,
        two_sided=two_sided,
        abs_spread=abs_spread,
        relative_spread=rel,
        iv_spread=iv_spread,
        volume=quote.volume,
        volume_usd=quote.volume_usd,
        open_interest=quote.open_interest,
        turnover=turnover,
        range_pct=range_pct,
        last_inside_nbbo=last_inside,
        zero_volume=zero_volume,
        stub_quote=stub_quote,
        liquidity_score=score,
        bucket=_bucket(score, stub_quote=stub_quote, zero_volume=zero_volume),
        flags=flags,
    )


def summarize_chain_liquidity(
    quotes: Iterable[DeribitOptionQuote],
    *,
    size: float = 0.1,
) -> ChainLiquiditySummary:
    """Summarize how tradable a full option chain looks at one snapshot."""

    quote_list = list(quotes)
    features = [liquidity_features(quote, size=size) for quote in quote_list]
    spreads = [item.relative_spread for item in features if item.relative_spread is not None]
    iv_spreads = [item.iv_spread for item in features if item.iv_spread is not None]
    bucket_counts: dict[str, int] = defaultdict(int)
    for item in features:
        bucket_counts[item.bucket] += 1

    snapshot_time = max((quote.snapshot_time for quote in quote_list), default=datetime.min)
    return ChainLiquiditySummary(
        snapshot_time=snapshot_time,
        contract_count=len(quote_list),
        two_sided_count=sum(1 for item in features if item.two_sided),
        zero_volume_count=sum(1 for item in features if item.zero_volume),
        median_relative_spread=_percentile(spreads, 0.5),
        p90_relative_spread=_percentile(spreads, 0.9),
        median_iv_spread=_percentile(iv_spreads, 0.5),
        contracts_with_volume_ge_size=sum(
            1 for quote in quote_list if (quote.volume or 0.0) >= size
        ),
        bucket_counts=dict(bucket_counts),
    )


def predetermined_limit_price(
    quote: DeribitOptionQuote,
    *,
    side: Side,
    passive_spreads: float = 1.0,
) -> float | None:
    """Build a resting limit from a *prior* quote, never from the same bar's range.

    ``passive_spreads=0`` joins the bid (buy) or ask (sell). ``1`` rests a full
    spread through the touch, which is the patient "wait for panic" style.
    """

    if quote.bid_price is None or quote.ask_price is None:
        return None
    spread = quote.ask_price - quote.bid_price
    if side == "buy":
        return quote.bid_price - passive_spreads * spread
    return quote.ask_price + passive_spreads * spread


def is_panic_quote(
    current: DeribitOptionQuote,
    previous: DeribitOptionQuote | None = None,
    *,
    underlying_move: float = 0.03,
    iv_jump: float = 5.0,
    range_pct: float = 0.25,
) -> bool:
    """Detect a panic bar from snapshot fields only."""

    center = mid_price(current)
    if (
        current.high_price is not None
        and current.low_price is not None
        and center
        and center > 0
        and (current.high_price - current.low_price) / center >= range_pct
    ):
        return True
    if current.price_change is not None and abs(current.price_change) >= underlying_move * 100.0:
        # Deribit ``price_change`` is a percent of the option price, not the index.
        if abs(current.price_change) >= 20.0:
            return True
    if previous is None:
        return False
    if (
        current.underlying_price
        and previous.underlying_price
        and previous.underlying_price > 0
        and abs(current.underlying_price / previous.underlying_price - 1.0) >= underlying_move
    ):
        return True
    if (
        current.mark_iv is not None
        and previous.mark_iv is not None
        and abs(current.mark_iv - previous.mark_iv) >= iv_jump
    ):
        return True
    return False


def is_panic_bar(
    bar: OhlcBar,
    previous: OhlcBar | None = None,
    *,
    range_pct: float = 0.20,
    volume_multiple: float = 3.0,
    typical_volume: float | None = None,
) -> bool:
    """Detect a panic print from an option OHLC bar."""

    basis = previous.close if previous is not None else bar.open
    if basis > 0 and (bar.high - bar.low) / basis >= range_pct:
        return True
    if typical_volume and typical_volume > 0 and bar.volume >= volume_multiple * typical_volume:
        return True
    return False


def simulate_resting_limit_on_snapshots(
    quotes: Sequence[DeribitOptionQuote],
    *,
    side: Side,
    size: float,
    passive_spreads: float = 1.0,
    max_participation: float = 0.1,
    require_panic: bool = True,
    min_fill_size: float = 0.1,
) -> RestingFillResult:
    """Estimate fills from a time-ordered quote history without using future extremes.

    The limit is set from snapshot ``t-1``. A fill at ``t`` requires the 24h
    low/high to trade through that predetermined limit, plus enough volume.
    """

    ordered = sorted(quotes, key=lambda quote: quote.snapshot_time)
    events: list[PassiveFillEvent] = []
    remaining = size
    limit_price = None
    previous: DeribitOptionQuote | None = None
    for quote in ordered:
        if remaining < min_fill_size:
            break
        if limit_price is None:
            limit_price = predetermined_limit_price(quote, side=side, passive_spreads=passive_spreads)
            previous = quote
            continue
        if previous is None:
            previous = quote
            continue
        touched = _snapshot_touched(quote, side=side, limit_price=limit_price)
        panic = is_panic_quote(quote, previous)
        if not touched or (require_panic and not panic):
            previous = quote
            continue
        fill_size = _capped_fill_size(remaining, quote.volume, max_participation, min_fill_size)
        if fill_size <= 0:
            previous = quote
            continue
        mtm = _conservative_mtm(quote, side=side)
        mtm_vs_fill = (mtm - limit_price) if side == "buy" else (limit_price - mtm)
        adverse = max(0.0, -mtm_vs_fill)
        events.append(
            PassiveFillEvent(
                timestamp=quote.snapshot_time,
                fill_price=limit_price,
                fill_size=fill_size,
                bar_open=previous.mark_price,
                bar_close=quote.mark_price,
                bar_volume=quote.volume,
                mtm_vs_fill=mtm_vs_fill,
                adverse_selection=adverse,
                panic=panic,
            )
        )
        remaining -= fill_size
        previous = quote

    fill_size = size - remaining
    return _fill_result(side, limit_price or 0.0, size, fill_size, events, max_participation)


def simulate_resting_limit_on_ohlc(
    bars: Sequence[OhlcBar],
    *,
    side: Side,
    limit_price: float,
    size: float,
    max_participation: float = 0.1,
    require_panic: bool = False,
    min_fill_size: float = 0.1,
) -> RestingFillResult:
    """Walk bars in time order and fill on the first genuine through-touch.

    The limit must be chosen *before* these bars. Fill price is the limit, not
    the bar low/high. Mark-to-market uses that bar's close, so a falling knife
    shows up as adverse selection instead of a perfect bottom tick.
    """

    typical_volume = _positive_median([bar.volume for bar in bars])
    events: list[PassiveFillEvent] = []
    remaining = size
    previous: OhlcBar | None = None
    for bar in bars:
        if remaining < min_fill_size:
            break
        touched = (bar.low <= limit_price) if side == "buy" else (bar.high >= limit_price)
        panic = is_panic_bar(bar, previous, typical_volume=typical_volume)
        previous = bar
        if not touched or bar.volume <= 0:
            continue
        if require_panic and not panic:
            continue
        fill_size = _capped_fill_size(remaining, bar.volume, max_participation, min_fill_size)
        if fill_size <= 0:
            continue
        mtm_vs_fill = (bar.close - limit_price) if side == "buy" else (limit_price - bar.close)
        events.append(
            PassiveFillEvent(
                timestamp=bar.timestamp,
                fill_price=limit_price,
                fill_size=fill_size,
                bar_open=bar.open,
                bar_close=bar.close,
                bar_volume=bar.volume,
                mtm_vs_fill=mtm_vs_fill,
                adverse_selection=max(0.0, -mtm_vs_fill),
                panic=panic,
            )
        )
        remaining -= fill_size

    fill_size = size - remaining
    return _fill_result(side, limit_price, size, fill_size, events, max_participation)


def assess_strategy_plausibility(
    quote: DeribitOptionQuote,
    *,
    side: Side,
    size: float,
    passive_spreads: float = 1.0,
    fill_result: RestingFillResult | None = None,
    assumed_edge: float | None = None,
) -> StrategyPlausibility:
    """Combine liquidity, capacity, spread tax, and fill quality into a verdict."""

    features = liquidity_features(quote, size=size)
    limit_price = predetermined_limit_price(quote, side=side, passive_spreads=passive_spreads)
    half_spread = None
    if features.abs_spread is not None:
        half_spread = features.abs_spread / 2.0
    size_pct = None
    if quote.volume and quote.volume > 0:
        size_pct = size / quote.volume

    notes: list[str] = list(features.flags)
    required_edge = half_spread
    if fill_result is not None and fill_result.median_adverse_selection is not None:
        required_edge = (required_edge or 0.0) + fill_result.median_adverse_selection
        notes.append(
            f"median_adverse_selection={fill_result.median_adverse_selection:.6g}"
        )

    verdict: PlausibilityVerdict
    if not features.two_sided and features.zero_volume:
        verdict = "untradable"
        notes.append("no two-sided book and no prints")
    elif size_pct is not None and size_pct > 0.25:
        verdict = "no_capacity"
        notes.append("size is more than 25% of 24h volume")
    elif features.zero_volume:
        verdict = "no_capacity"
        notes.append("zero 24h volume; a resting order may never print")
    elif features.relative_spread is not None and features.relative_spread >= 0.5:
        verdict = "spread_dominates"
        notes.append("relative spread is at least 50% of premium")
    elif (
        assumed_edge is not None
        and required_edge is not None
        and assumed_edge <= required_edge
    ):
        verdict = "spread_dominates"
        notes.append("stated edge does not cover spread plus adverse selection")
    elif fill_result is not None and not fill_result.filled:
        verdict = "fragile"
        notes.append("predetermined limit never touched printed range")
    elif features.bucket in {"liquid", "tradable_passive"} and (
        fill_result is None or fill_result.filled
    ):
        verdict = "plausible_if_patient"
        notes.append("small size can wait at a predetermined limit, but mark PnL is not executable")
    else:
        verdict = "fragile"
        notes.append("thin book: fills, if any, are likely stale and adversely selected")

    return StrategyPlausibility(
        instrument_name=quote.instrument_name,
        side=side,
        size=size,
        limit_price=limit_price,
        liquidity=features,
        half_spread_cost=half_spread,
        size_as_pct_of_volume=size_pct,
        fill_result=fill_result,
        required_edge=required_edge,
        verdict=verdict,
        notes=tuple(notes),
    )


def _liquidity_flags(
    *,
    two_sided: bool,
    rel: float | None,
    iv_spread: float | None,
    volume: float,
    open_interest: float | None,
    last_inside: bool | None,
    stub_quote: bool,
    size: float,
) -> tuple[str, ...]:
    flags: list[str] = []
    if not two_sided:
        flags.append("one_sided_quote")
    if stub_quote:
        flags.append("stub_quote")
    if rel is not None and rel >= 0.2:
        flags.append("wide_relative_spread")
    if iv_spread is not None and iv_spread >= 10.0:
        flags.append("wide_iv_spread")
    if volume <= 0:
        flags.append("zero_volume")
    elif volume < size:
        flags.append("size_exceeds_volume")
    if open_interest is not None and open_interest < 1:
        flags.append("tiny_open_interest")
    if last_inside is False:
        flags.append("stale_last")
    return tuple(flags)


def _liquidity_score(
    *,
    two_sided: bool,
    rel: float | None,
    volume: float,
    open_interest: float | None,
    stub_quote: bool,
) -> float:
    quote_score = 25.0 if two_sided else 0.0
    if rel is None:
        spread_score = 0.0
    else:
        spread_score = 25.0 * math.exp(-max(rel, 0.0) / 0.10)
    volume_score = 25.0 * min(1.0, math.log1p(max(volume, 0.0)) / math.log1p(50.0))
    oi_value = open_interest or 0.0
    oi_score = 25.0 * min(1.0, math.log1p(max(oi_value, 0.0)) / math.log1p(100.0))
    score = quote_score + spread_score + volume_score + oi_score
    if stub_quote:
        score *= 0.5
    return round(max(0.0, min(score, 100.0)), 2)


def _bucket(score: float, *, stub_quote: bool, zero_volume: bool) -> LiquidityBucket:
    if stub_quote and zero_volume:
        return "unusable"
    if score >= 70:
        return "liquid"
    if score >= 40:
        return "tradable_passive"
    if score >= 20:
        return "fragile"
    return "unusable"


def _coin_vega_per_vol_point(quote: DeribitOptionQuote, *, as_of: date | None = None) -> float | None:
    if (
        quote.underlying_price is None
        or quote.underlying_price <= 0
        or quote.strike <= 0
        or quote.mark_iv is None
        or quote.mark_iv <= 0
    ):
        return None
    snapshot_date = as_of or quote.snapshot_time.date()
    years = max((quote.expiration - snapshot_date).days, 0) / 365.0
    if years <= 1e-6:
        return None
    sigma = quote.mark_iv / 100.0
    vol_sqrt_t = sigma * math.sqrt(years)
    if vol_sqrt_t <= 0:
        return None
    d1 = (math.log(quote.underlying_price / quote.strike) + 0.5 * sigma * sigma * years) / vol_sqrt_t
    # Coin-quoted Black-76 vega per 1.00 vol, then scale to one vol point.
    return _norm_pdf(d1) * math.sqrt(years) * 0.01


def _norm_pdf(value: float) -> float:
    return math.exp(-0.5 * value * value) / math.sqrt(2.0 * math.pi)


def _percentile(values: Sequence[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if quantile <= 0:
        return ordered[0]
    if quantile >= 1:
        return ordered[-1]
    index = min(len(ordered) - 1, max(0, int(math.ceil(quantile * len(ordered)) - 1)))
    return ordered[index]


def _snapshot_touched(quote: DeribitOptionQuote, *, side: Side, limit_price: float) -> bool:
    if side == "buy":
        low = quote.low_price
        if low is None:
            low = quote.last_price
        return low is not None and low <= limit_price
    high = quote.high_price
    if high is None:
        high = quote.last_price
    return high is not None and high >= limit_price


def _capped_fill_size(
    remaining: float,
    volume: float | None,
    max_participation: float,
    min_fill_size: float,
) -> float:
    printed = volume or 0.0
    available = printed * max_participation
    fill_size = min(remaining, available)
    if fill_size + 1e-12 < min_fill_size:
        return 0.0
    return fill_size


def _conservative_mtm(quote: DeribitOptionQuote, *, side: Side) -> float:
    if side == "buy":
        for value in (quote.bid_price, quote.mark_price, quote.last_price, quote.mid_price):
            if value is not None:
                return value
    else:
        for value in (quote.ask_price, quote.mark_price, quote.last_price, quote.mid_price):
            if value is not None:
                return value
    return 0.0


def _positive_median(values: Sequence[float]) -> float | None:
    positive = [value for value in values if value > 0]
    if not positive:
        return None
    return float(median(positive))


def _fill_result(
    side: Side,
    limit_price: float,
    size: float,
    fill_size: float,
    events: Sequence[PassiveFillEvent],
    max_participation: float,
) -> RestingFillResult:
    adverses = [event.adverse_selection for event in events]
    mtms = [event.mtm_vs_fill for event in events]
    return RestingFillResult(
        side=side,
        limit_price=limit_price,
        requested_size=size,
        filled=fill_size > 0,
        fill_size=fill_size,
        fill_rate=fill_size / size if size else 0.0,
        events=tuple(events),
        median_adverse_selection=float(median(adverses)) if adverses else None,
        mean_mtm_vs_fill=sum(mtms) / len(mtms) if mtms else None,
        participation_used=max_participation,
    )
