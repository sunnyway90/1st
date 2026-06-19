"""Command line entry point for Deribit BTC option snapshots."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from deribit_options.core import (
    AtmOptionDailyChange,
    AtmOptionPoint,
    append_option_snapshot_csv,
    atm_daily_changes,
    fetch_btc_option_snapshot,
    read_option_quotes_csv,
    select_atm_option_pair,
)


def main() -> None:
    """Fetch a live snapshot or analyze a stored BTC ATM option history."""

    parser = argparse.ArgumentParser(description="Deribit BTC option ATM daily analysis")
    parser.add_argument("--snapshot-csv", type=Path, help="append a live BTC option snapshot to this CSV file")
    parser.add_argument("--history-csv", type=Path, help="read stored snapshots and print ATM daily changes")
    parser.add_argument("--target-expiration", type=date.fromisoformat, help="track one expiry, YYYY-MM-DD")
    parser.add_argument("--target-days-to-expiration", type=int, help="track the expiry closest to this tenor")
    parser.add_argument("--min-days-to-expiration", type=int, default=1, help="minimum remaining days, default 1")
    args = parser.parse_args()

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
        changes = atm_daily_changes(
            read_option_quotes_csv(args.history_csv),
            target_expiration=args.target_expiration,
            target_days_to_expiration=args.target_days_to_expiration,
            min_days_to_expiration=args.min_days_to_expiration,
        )
        _print_changes(changes)


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


def _format_optional(value: float | None) -> str:
    return "" if value is None else f"{value:.6g}"


if __name__ == "__main__":
    main()
