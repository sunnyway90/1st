"""Tests for Deribit BTC option data utilities."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from deribit_options import (
    DeribitOptionQuote,
    atm_daily_changes,
    build_option_quotes,
    parse_option_instrument_name,
    read_option_quotes_csv,
    select_atm_option_pair,
    write_option_quotes_csv,
)


class DeribitOptionTests(unittest.TestCase):
    """Validate Deribit option parsing and ATM daily analysis."""

    def test_parse_option_instrument_name(self) -> None:
        """Deribit option symbols should unpack expiry, strike, and type."""

        parsed = parse_option_instrument_name("BTC-9DEC24-102000-C")

        self.assertEqual(parsed.base_currency, "BTC")
        self.assertEqual(parsed.expiration, date(2024, 12, 9))
        self.assertEqual(parsed.strike, 102000.0)
        self.assertEqual(parsed.option_type, "call")

    def test_build_option_quotes_merges_instruments_and_summaries(self) -> None:
        """Quote rows should combine static instrument metadata with book summaries."""

        quotes = build_option_quotes(
            [
                {
                    "instrument_name": "BTC-27JUN25-100000-C",
                    "expiration_timestamp": 1751007600000,
                    "strike": 100000,
                    "option_type": "call",
                }
            ],
            [
                {
                    "instrument_name": "BTC-27JUN25-100000-C",
                    "underlying_price": 100500,
                    "mark_iv": 52.5,
                    "mark_price": 0.05,
                    "open_interest": 12,
                    "volume": 3,
                }
            ],
            as_of=datetime(2025, 6, 20, 12, tzinfo=timezone.utc),
        )

        self.assertEqual(len(quotes), 1)
        self.assertEqual(quotes[0].expiration, date(2025, 6, 27))
        self.assertEqual(quotes[0].option_type, "call")
        self.assertEqual(quotes[0].underlying_price, 100500.0)
        self.assertEqual(quotes[0].mark_iv, 52.5)

    def test_select_atm_pair_prefers_nearest_strike_with_call_and_put(self) -> None:
        """ATM selection should choose the nearest strike and return both sides."""

        quotes = _quotes_for_day(date(2025, 6, 20), underlying=100800, strikes=(100000, 105000))

        point = select_atm_option_pair(quotes, as_of_date=date(2025, 6, 20))

        self.assertIsNotNone(point)
        assert point is not None
        self.assertEqual(point.strike, 100000.0)
        self.assertEqual(point.expiration, date(2025, 6, 27))
        self.assertEqual(point.call_instrument_name, "BTC-27JUN25-100000-C")
        self.assertEqual(point.put_instrument_name, "BTC-27JUN25-100000-P")
        self.assertAlmostEqual(point.average_mark_iv or 0.0, 51.0)
        self.assertAlmostEqual(point.straddle_mark_price or 0.0, 0.115)

    def test_atm_daily_changes_uses_latest_snapshot_per_day(self) -> None:
        """Daily changes should compare each day's latest stored ATM snapshot."""

        stale_day_one = _quotes_for_day(
            date(2025, 6, 20),
            underlying=99000,
            strikes=(95000, 100000),
            hour=8,
        )
        latest_day_one = _quotes_for_day(
            date(2025, 6, 20),
            underlying=100800,
            strikes=(100000, 105000),
            hour=16,
        )
        day_two = _quotes_for_day(date(2025, 6, 21), underlying=104200, strikes=(100000, 105000), hour=16)

        changes = atm_daily_changes(stale_day_one + latest_day_one + day_two)

        self.assertEqual(len(changes), 2)
        self.assertEqual(changes[0].point.strike, 100000.0)
        self.assertIsNone(changes[0].underlying_change)
        self.assertEqual(changes[1].point.strike, 105000.0)
        self.assertAlmostEqual(changes[1].underlying_change or 0.0, 3400.0)
        self.assertAlmostEqual(changes[1].strike_change or 0.0, 5000.0)
        self.assertAlmostEqual(changes[1].average_mark_iv_change or 0.0, 2.5)

    def test_csv_round_trip_preserves_quotes(self) -> None:
        """CSV history files should round-trip quote observations."""

        quotes = _quotes_for_day(date(2025, 6, 20), underlying=100800, strikes=(100000,))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "btc_options.csv"

            write_option_quotes_csv(path, quotes)
            loaded = read_option_quotes_csv(path)

        self.assertEqual(loaded, quotes)


def _quotes_for_day(
    snapshot_date: date,
    *,
    underlying: float,
    strikes: tuple[int, ...],
    hour: int = 16,
) -> list[DeribitOptionQuote]:
    expiration = date(2025, 6, 27)
    snapshot_time = datetime(snapshot_date.year, snapshot_date.month, snapshot_date.day, hour, tzinfo=timezone.utc)
    quotes: list[DeribitOptionQuote] = []
    for strike in strikes:
        for suffix, option_type, iv_offset, mark_price in (
            ("C", "call", 0.5, 0.07 if strike >= underlying else 0.06),
            ("P", "put", 1.5, 0.055 if strike <= underlying else 0.065),
        ):
            quotes.append(
                DeribitOptionQuote(
                    snapshot_time=snapshot_time,
                    instrument_name=f"BTC-27JUN25-{strike}-{suffix}",
                    expiration=expiration,
                    strike=float(strike),
                    option_type=option_type,
                    underlying_price=underlying,
                    mark_iv=50.0 + (strike - 100000) / 2000.0 + iv_offset,
                    mark_price=mark_price,
                    open_interest=10.0,
                    volume=1.0,
                )
            )
    return quotes


if __name__ == "__main__":
    unittest.main()
