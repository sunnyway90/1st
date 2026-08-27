"""Command line entry point for Deribit BTC option snapshots."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from deribit_options.core import (
    AtmOptionDailyChange,
    AtmOptionPoint,
    DeribitOptionQuote,
    DeribitPublicClient,
    append_option_snapshot_csv,
    atm_daily_changes,
    fetch_btc_option_snapshot,
    read_option_quotes_csv,
    select_atm_option_pair,
)
from deribit_options.liquidity import (
    Side,
    assess_strategy_plausibility,
    liquidity_features,
    predetermined_limit_price,
    simulate_resting_limit_on_ohlc,
    simulate_resting_limit_on_snapshots,
    summarize_chain_liquidity,
)


def main() -> None:
    """Fetch a live snapshot or analyze a stored BTC ATM option history."""

    parser = argparse.ArgumentParser(description="Deribit BTC option ATM and liquidity analysis")
    parser.add_argument("--snapshot-csv", type=Path, help="append a live BTC option snapshot to this CSV file")
    parser.add_argument("--history-csv", type=Path, help="read stored snapshots and print ATM daily changes")
    parser.add_argument("--target-expiration", type=date.fromisoformat, help="track one expiry, YYYY-MM-DD")
    parser.add_argument("--target-days-to-expiration", type=int, help="track the expiry closest to this tenor")
    parser.add_argument("--min-days-to-expiration", type=int, default=1, help="minimum remaining days, default 1")
    parser.add_argument("--liquidity", action="store_true", help="score chain liquidity from a live or stored snapshot")
    parser.add_argument("--fill-sim", action="store_true", help="estimate a patient resting-limit fill without tick data")
    parser.add_argument("--instrument", help="option instrument for fill simulation; default is the ATM pair")
    parser.add_argument("--side", choices=("buy", "sell"), default="buy", help="resting order side, default buy")
    parser.add_argument("--size", type=float, default=0.1, help="order size in contracts, default 0.1")
    parser.add_argument(
        "--passive-spreads",
        type=float,
        default=1.0,
        help="how many spreads through the touch to rest, default 1.0",
    )
    parser.add_argument("--resolution", default="60", help="OHLC resolution for fill simulation, default 60 minutes")
    parser.add_argument("--lookback-hours", type=int, default=168, help="OHLC lookback window, default 168")
    parser.add_argument(
        "--require-panic",
        action="store_true",
        help="only count fills on panic bars or panic snapshots",
    )
    args = parser.parse_args()

    quotes: list[DeribitOptionQuote] | None = None
    if args.snapshot_csv:
        quotes = fetch_btc_option_snapshot()
        append_option_snapshot_csv(args.snapshot_csv, quotes)
        point = select_atm_option_pair(
            quotes,
            target_expiration=args.target_expiration,
            target_days_to_expiration=args.target_days_to_expiration,
            min_days_to_expiration=args.min_days_to_expiration,
        )
        print(f"Appended {len(quotes)} BTC option quotes to {args.snapshot_csv}")
        if point:
            _print_point(point)

    if args.history_csv:
        stored = read_option_quotes_csv(args.history_csv)
        if quotes is None:
            quotes = stored
        changes = atm_daily_changes(
            stored,
            target_expiration=args.target_expiration,
            target_days_to_expiration=args.target_days_to_expiration,
            min_days_to_expiration=args.min_days_to_expiration,
        )
        _print_changes(changes)
        if args.fill_sim:
            _print_snapshot_fill_sim(
                stored,
                instrument_name=args.instrument,
                side=_side(args.side),
                size=args.size,
                passive_spreads=args.passive_spreads,
                require_panic=args.require_panic,
                target_expiration=args.target_expiration,
                target_days_to_expiration=args.target_days_to_expiration,
                min_days_to_expiration=args.min_days_to_expiration,
            )

    if args.liquidity or (args.fill_sim and args.history_csv is None):
        if quotes is None:
            quotes = fetch_btc_option_snapshot()
        if args.liquidity:
            _print_liquidity(
                quotes,
                size=args.size,
                side=_side(args.side),
                passive_spreads=args.passive_spreads,
                target_expiration=args.target_expiration,
                target_days_to_expiration=args.target_days_to_expiration,
                min_days_to_expiration=args.min_days_to_expiration,
            )
        if args.fill_sim and args.history_csv is None:
            _print_ohlc_fill_sim(
                quotes,
                instrument_name=args.instrument,
                side=_side(args.side),
                size=args.size,
                passive_spreads=args.passive_spreads,
                resolution=args.resolution,
                lookback_hours=args.lookback_hours,
                require_panic=args.require_panic,
                target_expiration=args.target_expiration,
                target_days_to_expiration=args.target_days_to_expiration,
                min_days_to_expiration=args.min_days_to_expiration,
            )


def _print_point(point: AtmOptionPoint) -> None:
    print(
        "ATM "
        f"{point.snapshot_date} expiry={point.expiration} strike={point.strike:g} "
        f"underlying={point.underlying_price:.2f} avg_mark_iv={_format_optional(point.average_mark_iv)}"
    )


def _print_changes(changes: list[AtmOptionDailyChange]) -> None:
    print("date,expiry,strike,underlying,avg_mark_iv,straddle_mark,underlying_chg,iv_chg,straddle_chg")
    for change in changes:
        point = change.point
        print(
            f"{point.snapshot_date},{point.expiration},{point.strike:g},"
            f"{point.underlying_price:.2f},{_format_optional(point.average_mark_iv)},"
            f"{_format_optional(point.straddle_mark_price)},"
            f"{_format_optional(change.underlying_change)},"
            f"{_format_optional(change.average_mark_iv_change)},"
            f"{_format_optional(change.straddle_mark_price_change)}"
        )


def _print_liquidity(
    quotes: list[DeribitOptionQuote],
    *,
    size: float,
    side: Side,
    passive_spreads: float,
    target_expiration: date | None,
    target_days_to_expiration: int | None,
    min_days_to_expiration: int,
) -> None:
    quote_times = {quote.snapshot_time for quote in quotes}
    if quote_times:
        latest = max(quote_times)
        quotes = [quote for quote in quotes if quote.snapshot_time == latest]
    summary = summarize_chain_liquidity(quotes, size=size)
    print("liquidity_snapshot," + summary.snapshot_time.isoformat())
    print(
        "contracts,two_sided,zero_volume,median_rel_spread,p90_rel_spread,median_iv_spread,volume_ge_size"
    )
    print(
        f"{summary.contract_count},{summary.two_sided_count},{summary.zero_volume_count},"
        f"{_format_optional(summary.median_relative_spread)},{_format_optional(summary.p90_relative_spread)},"
        f"{_format_optional(summary.median_iv_spread)},{summary.contracts_with_volume_ge_size}"
    )
    print("bucket_counts," + ",".join(f"{name}={count}" for name, count in sorted(summary.bucket_counts.items())))

    point = select_atm_option_pair(
        quotes,
        target_expiration=target_expiration,
        target_days_to_expiration=target_days_to_expiration,
        min_days_to_expiration=min_days_to_expiration,
    )
    examples: list[DeribitOptionQuote] = []
    if point and point.call_instrument_name:
        atm = _quote_by_name(quotes, point.call_instrument_name)
        if atm:
            examples.append(atm)
    two_sided = [quote for quote in quotes if quote.bid_price is not None and quote.ask_price is not None]
    if two_sided:
        examples.append(min(two_sided, key=lambda quote: liquidity_features(quote, size=size).liquidity_score))
    if quotes:
        examples.append(min(quotes, key=lambda quote: liquidity_features(quote, size=size).liquidity_score))

    print("instrument,score,bucket,rel_spread,iv_spread,volume,oi,verdict,limit,required_edge,flags")
    seen: set[str] = set()
    for quote in examples:
        if quote.instrument_name in seen:
            continue
        seen.add(quote.instrument_name)
        report = assess_strategy_plausibility(
            quote,
            side=side,
            size=size,
            passive_spreads=passive_spreads,
        )
        features = report.liquidity
        print(
            f"{quote.instrument_name},{features.liquidity_score:.2f},{features.bucket},"
            f"{_format_optional(features.relative_spread)},{_format_optional(features.iv_spread)},"
            f"{_format_optional(features.volume)},{_format_optional(features.open_interest)},"
            f"{report.verdict},{_format_optional(report.limit_price)},{_format_optional(report.required_edge)},"
            f"{'|'.join(note.replace(',', ';') for note in report.notes)}"
        )


def _print_ohlc_fill_sim(
    quotes: list[DeribitOptionQuote],
    *,
    instrument_name: str | None,
    side: Side,
    size: float,
    passive_spreads: float,
    resolution: str,
    lookback_hours: int,
    require_panic: bool,
    target_expiration: date | None,
    target_days_to_expiration: int | None,
    min_days_to_expiration: int,
) -> None:
    quote = _select_sim_quote(
        quotes,
        instrument_name=instrument_name,
        target_expiration=target_expiration,
        target_days_to_expiration=target_days_to_expiration,
        min_days_to_expiration=min_days_to_expiration,
    )
    if quote is None:
        print("fill_sim,no_instrument")
        return
    if quote.bid_price is None or quote.ask_price is None:
        print(f"fill_sim,{quote.instrument_name},no_two_sided_quote")
        return

    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=lookback_hours)
    client = DeribitPublicClient()
    bars = client.get_tradingview_chart_data(
        quote.instrument_name,
        start_timestamp_ms=int(start.timestamp() * 1000),
        end_timestamp_ms=int(end.timestamp() * 1000),
        resolution=resolution,
    )
    if len(bars) < 2:
        print(f"fill_sim,{quote.instrument_name},insufficient_ohlc")
        return
    spread = quote.ask_price - quote.bid_price
    if side == "buy":
        limit_price = bars[0].close - passive_spreads * spread
        if limit_price <= 0:
            print(f"fill_sim,{quote.instrument_name},non_positive_limit")
            return
    else:
        limit_price = bars[0].close + passive_spreads * spread
    result = simulate_resting_limit_on_ohlc(
        bars[1:],
        side=side,
        limit_price=limit_price,
        size=size,
        require_panic=require_panic,
    )
    report = assess_strategy_plausibility(
        quote,
        side=side,
        size=size,
        passive_spreads=passive_spreads,
        fill_result=result,
    )
    _print_fill_result(quote, report, bar_count=len(bars) - 1, source="ohlc")


def _print_snapshot_fill_sim(
    quotes: list[DeribitOptionQuote],
    *,
    instrument_name: str | None,
    side: Side,
    size: float,
    passive_spreads: float,
    require_panic: bool,
    target_expiration: date | None,
    target_days_to_expiration: int | None,
    min_days_to_expiration: int,
) -> None:
    quote = _select_sim_quote(
        quotes,
        instrument_name=instrument_name,
        target_expiration=target_expiration,
        target_days_to_expiration=target_days_to_expiration,
        min_days_to_expiration=min_days_to_expiration,
    )
    if quote is None:
        print("fill_sim,no_instrument")
        return
    series = [item for item in quotes if item.instrument_name == quote.instrument_name]
    result = simulate_resting_limit_on_snapshots(
        series,
        side=side,
        size=size,
        passive_spreads=passive_spreads,
        require_panic=require_panic,
    )
    report = assess_strategy_plausibility(
        quote,
        side=side,
        size=size,
        passive_spreads=passive_spreads,
        fill_result=result,
    )
    _print_fill_result(quote, report, bar_count=len(series), source="snapshots")


def _print_fill_result(
    quote: DeribitOptionQuote,
    report,
    *,
    bar_count: int,
    source: str,
) -> None:
    result = report.fill_result
    print(
        "fill_sim_source,instrument,side,size,limit,bars,filled,fill_size,fill_rate,"
        "median_adverse,mean_mtm_vs_fill,verdict,required_edge"
    )
    if result is None:
        print(f"{source},{quote.instrument_name},{report.side},{report.size},,,,,,")
        return
    print(
        f"{source},{quote.instrument_name},{result.side},{result.requested_size},"
        f"{result.limit_price:.6g},{bar_count},{int(result.filled)},{result.fill_size:.6g},"
        f"{result.fill_rate:.4f},{_format_optional(result.median_adverse_selection)},"
        f"{_format_optional(result.mean_mtm_vs_fill)},{report.verdict},"
        f"{_format_optional(report.required_edge)}"
    )
    if result.events:
        print("fill_time,fill_price,fill_size,close,mtm_vs_fill,adverse,panic")
        for event in result.events:
            print(
                f"{event.timestamp.isoformat()},{event.fill_price:.6g},{event.fill_size:.6g},"
                f"{_format_optional(event.bar_close)},{event.mtm_vs_fill:.6g},"
                f"{event.adverse_selection:.6g},{int(event.panic)}"
            )


def _select_sim_quote(
    quotes: list[DeribitOptionQuote],
    *,
    instrument_name: str | None,
    target_expiration: date | None,
    target_days_to_expiration: int | None,
    min_days_to_expiration: int,
) -> DeribitOptionQuote | None:
    if instrument_name:
        return _quote_by_name(quotes, instrument_name)
    point = select_atm_option_pair(
        quotes,
        target_expiration=target_expiration,
        target_days_to_expiration=target_days_to_expiration,
        min_days_to_expiration=min_days_to_expiration,
    )
    if point is None:
        return None
    name = point.call_instrument_name or point.put_instrument_name
    if name is None:
        return None
    return _quote_by_name(quotes, name)


def _quote_by_name(quotes: list[DeribitOptionQuote], instrument_name: str) -> DeribitOptionQuote | None:
    latest: DeribitOptionQuote | None = None
    for quote in quotes:
        if quote.instrument_name != instrument_name:
            continue
        if latest is None or quote.snapshot_time >= latest.snapshot_time:
            latest = quote
    return latest


def _side(value: str) -> Side:
    if value == "sell":
        return "sell"
    return "buy"


def _format_optional(value: float | None) -> str:
    return "" if value is None else f"{value:.6g}"


if __name__ == "__main__":
    main()
