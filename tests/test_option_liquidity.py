"""Tests for option liquidity scoring and no-tick resting-limit fills."""

from __future__ import annotations

import unittest
from datetime import date, datetime, timedelta, timezone

from deribit_options.core import DeribitOptionQuote, OhlcBar
from deribit_options.liquidity import (
    assess_strategy_plausibility,
    estimate_iv_spread,
    liquidity_features,
    predetermined_limit_price,
    relative_spread,
    simulate_resting_limit_on_ohlc,
    simulate_resting_limit_on_snapshots,
    summarize_chain_liquidity,
)


class OptionLiquidityTests(unittest.TestCase):
    """Validate spread, capacity, and fill rules that do not need tick data."""

    def test_relative_spread_and_stub_flags(self) -> None:
        """Wide one-sided quotes should be flagged as unusable stubs."""

        tight = _quote(bid=0.020, ask=0.021, volume=80, open_interest=200)
        wide = _quote(bid=0.001, ask=0.004, volume=0.2, open_interest=1)
        stub = _quote(bid=None, ask=0.0001, volume=0.0, open_interest=0.2)

        self.assertAlmostEqual(relative_spread(tight) or 0.0, 1.0 / 20.5, places=6)
        self.assertGreater(liquidity_features(tight).liquidity_score, liquidity_features(wide).liquidity_score)
        self.assertEqual(liquidity_features(tight).bucket, "liquid")
        self.assertIn(liquidity_features(wide).bucket, {"fragile", "tradable_passive", "unusable"})
        self.assertTrue(liquidity_features(stub).stub_quote)
        self.assertEqual(liquidity_features(stub).bucket, "unusable")
        self.assertIn("one_sided_quote", liquidity_features(stub).flags)

    def test_iv_spread_converts_price_width_into_vol_points(self) -> None:
        """ATM vega should turn a 0.001 coin spread into about one vol point."""

        quote = _quote(bid=0.055, ask=0.056, mark_iv=50.0, strike=100000, underlying=100000)
        iv_spread = estimate_iv_spread(quote)

        self.assertIsNotNone(iv_spread)
        assert iv_spread is not None
        self.assertGreater(iv_spread, 0.3)
        self.assertLess(iv_spread, 3.0)

    def test_predetermined_limit_is_more_passive_than_the_touch(self) -> None:
        """A panic-wait buy sits below the bid, never at the same-bar low."""

        quote = _quote(bid=0.020, ask=0.024)
        buy_limit = predetermined_limit_price(quote, side="buy", passive_spreads=1.0)
        sell_limit = predetermined_limit_price(quote, side="sell", passive_spreads=1.0)

        self.assertAlmostEqual(buy_limit or 0.0, 0.016)
        self.assertAlmostEqual(sell_limit or 0.0, 0.028)
        cheap = _quote(bid=0.0001, ask=0.0004)
        self.assertIsNone(predetermined_limit_price(cheap, side="buy", passive_spreads=1.0))

    def test_ohlc_fill_uses_limit_not_bar_low(self) -> None:
        """Buying the day's low would look ahead; the fill price must stay at the limit."""

        start = datetime(2025, 6, 20, 8, tzinfo=timezone.utc)
        bars = [
            OhlcBar(start, open=0.020, high=0.021, low=0.019, close=0.020, volume=5),
            OhlcBar(start + timedelta(hours=1), open=0.019, high=0.0195, low=0.012, close=0.013, volume=8),
            OhlcBar(start + timedelta(hours=2), open=0.013, high=0.018, low=0.013, close=0.017, volume=3),
        ]

        result = simulate_resting_limit_on_ohlc(bars, side="buy", limit_price=0.016, size=0.1)

        self.assertTrue(result.filled)
        self.assertEqual(len(result.events), 1)
        self.assertAlmostEqual(result.events[0].fill_price, 0.016)
        self.assertAlmostEqual(result.events[0].fill_size, 0.1)
        self.assertAlmostEqual(result.events[0].mtm_vs_fill, 0.013 - 0.016)
        self.assertGreater(result.events[0].adverse_selection, 0.0)
        self.assertTrue(result.events[0].panic)

    def test_ohlc_requires_a_print_and_caps_participation(self) -> None:
        """A touch with no volume is not a fill, and size cannot take the whole bar."""

        start = datetime(2025, 6, 20, 8, tzinfo=timezone.utc)
        silent = [
            OhlcBar(start, open=0.02, high=0.02, low=0.01, close=0.011, volume=0),
        ]
        thin = [
            OhlcBar(start, open=0.02, high=0.02, low=0.01, close=0.011, volume=0.5),
        ]

        missed = simulate_resting_limit_on_ohlc(silent, side="buy", limit_price=0.016, size=0.1)
        partial = simulate_resting_limit_on_ohlc(
            thin,
            side="buy",
            limit_price=0.016,
            size=0.1,
            max_participation=0.1,
        )

        self.assertFalse(missed.filled)
        self.assertFalse(partial.filled)
        self.assertEqual(partial.fill_size, 0.0)

    def test_snapshot_fill_sets_limit_before_seeing_the_range(self) -> None:
        """Day-two high/low may trigger a fill, but the limit comes from day one."""

        day_one = _quote(bid=0.020, ask=0.024, volume=2, hour=16, day=20, low=0.019, high=0.025)
        day_two = _quote(
            bid=0.012,
            ask=0.018,
            volume=5,
            hour=16,
            day=21,
            low=0.010,
            high=0.019,
            mark=0.013,
            underlying=92000,
            mark_iv=70.0,
        )

        result = simulate_resting_limit_on_snapshots(
            [day_one, day_two],
            side="buy",
            size=0.1,
            passive_spreads=1.0,
            require_panic=True,
            max_participation=0.1,
        )

        self.assertTrue(result.filled)
        self.assertAlmostEqual(result.limit_price, 0.016)
        self.assertAlmostEqual(result.events[0].fill_price, 0.016)
        self.assertTrue(result.events[0].panic)
        self.assertGreater(result.events[0].adverse_selection, 0.0)

    def test_snapshot_does_not_fill_without_a_through_touch(self) -> None:
        """If the printed range never reaches the resting bid, the order waits."""

        day_one = _quote(bid=0.020, ask=0.024, volume=2, hour=16, day=20, low=0.019, high=0.025)
        day_two = _quote(bid=0.019, ask=0.023, volume=4, hour=16, day=21, low=0.018, high=0.024)

        result = simulate_resting_limit_on_snapshots(
            [day_one, day_two],
            side="buy",
            size=0.1,
            passive_spreads=1.0,
            require_panic=False,
        )

        self.assertFalse(result.filled)

    def test_strategy_plausibility_rejects_zero_volume_stubs(self) -> None:
        """A wide, silent contract should not look tradable just because size is small."""

        stub = _quote(bid=None, ask=0.0001, volume=0.0, open_interest=0.0)
        report = assess_strategy_plausibility(stub, side="buy", size=0.1)

        self.assertEqual(report.verdict, "untradable")
        self.assertIsNone(report.limit_price)

    def test_chain_summary_counts_zero_volume_and_capacity(self) -> None:
        """The chain summary should show how much of the book a small order can use."""

        quotes = [
            _quote(bid=0.020, ask=0.021, volume=80, open_interest=200, strike=100000),
            _quote(bid=0.001, ask=0.004, volume=0.0, open_interest=0.4, strike=70000, name_suffix="P"),
        ]

        summary = summarize_chain_liquidity(quotes, size=0.1)

        self.assertEqual(summary.contract_count, 2)
        self.assertEqual(summary.zero_volume_count, 1)
        self.assertEqual(summary.contracts_with_volume_ge_size, 1)
        self.assertGreater(summary.median_relative_spread or 0.0, 0.0)


def _quote(
    *,
    bid: float | None,
    ask: float | None,
    volume: float = 1.0,
    open_interest: float = 10.0,
    mark_iv: float = 50.0,
    strike: float = 100000.0,
    underlying: float = 100000.0,
    hour: int = 16,
    day: int = 20,
    low: float | None = None,
    high: float | None = None,
    mark: float | None = None,
    name_suffix: str = "C",
) -> DeribitOptionQuote:
    mid = None if bid is None or ask is None else (bid + ask) / 2.0
    return DeribitOptionQuote(
        snapshot_time=datetime(2025, 6, day, hour, tzinfo=timezone.utc),
        instrument_name=f"BTC-27JUN25-{int(strike)}-{name_suffix}",
        expiration=date(2025, 6, 27),
        strike=strike,
        option_type="call" if name_suffix == "C" else "put",
        underlying_price=underlying,
        mark_iv=mark_iv,
        mark_price=mark if mark is not None else mid,
        bid_price=bid,
        ask_price=ask,
        mid_price=mid,
        open_interest=open_interest,
        volume=volume,
        high_price=high,
        low_price=low,
        last_price=mark if mark is not None else mid,
    )


if __name__ == "__main__":
    unittest.main()
