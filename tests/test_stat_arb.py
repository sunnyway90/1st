"""Tests for the statistical-arbitrage / pairs-trading module."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from stat_arb import (
    FairRatioCoef,
    FundamentalSnapshot,
    PairStrategyConfig,
    adf_test,
    candidate_pairs,
    construct_spread,
    detect_regime_break,
    engle_granger,
    estimate_fair_ratio_coefs,
    estimate_hedge_ratio,
    fit_ou,
    fundamental_distance,
    generate_cointegrated_pair,
    generate_independent_pair,
    hurst_exponent,
    johansen_trace,
    load_pair_csv,
    pair_leg_weights,
    relative_value_mispricing,
    rolling_zscore,
    run_pair_backtest,
    screen_pair,
    variance_ratio,
)


class FundamentalTests(unittest.TestCase):
    """Validate fundamental distance, fair value, and pair candidacy."""

    def test_distance_is_zero_for_identical_snapshots(self) -> None:
        """Two identical names should have zero fundamental distance."""

        snap = FundamentalSnapshot("A", industry="bank", roe=0.1, net_margin=0.2, pe=8.0, pb=1.0, leverage=1.0)
        self.assertAlmostEqual(fundamental_distance(snap, snap), 0.0)

    def test_candidate_pairs_keep_same_industry_and_threshold(self) -> None:
        """Only close same-industry names should survive the first screen."""

        names = [
            FundamentalSnapshot("CITIC", industry="broker", roe=0.12, net_margin=0.25, pe=12.0, pb=1.4, leverage=1.8),
            FundamentalSnapshot("HTSC", industry="broker", roe=0.11, net_margin=0.24, pe=12.5, pb=1.5, leverage=1.9),
            FundamentalSnapshot("AIR", industry="airline", roe=0.12, net_margin=0.25, pe=12.0, pb=1.4, leverage=1.8),
        ]
        pairs = candidate_pairs(names, max_distance=0.2, require_same_industry=True)
        self.assertEqual(len(pairs), 1)
        self.assertEqual({pairs[0][0].ticker, pairs[0][1].ticker}, {"CITIC", "HTSC"})

    def test_fair_ratio_ols_recovers_coefficients(self) -> None:
        """Fair-ratio OLS should recover a known linear mapping."""

        rng = np.random.default_rng(3)
        eps = rng.uniform(0.8, 1.3, 80)
        roe = rng.uniform(0.8, 1.2, 80)
        margin = rng.uniform(0.7, 1.1, 80)
        ratio = 0.2 + 0.9 * eps + 0.3 * roe + 0.1 * margin + rng.normal(0.0, 0.01, 80)
        coef = estimate_fair_ratio_coefs(ratio, eps, roe, margin)
        self.assertAlmostEqual(coef.alpha, 0.2, places=1)
        self.assertAlmostEqual(coef.eps, 0.9, places=1)

    def test_mispricing_positive_when_price_ratio_exceeds_fair(self) -> None:
        """A rich A/B price ratio should produce positive mispricing."""

        first = FundamentalSnapshot("A", eps=2.0, roe=0.10, net_margin=0.20)
        second = FundamentalSnapshot("B", eps=1.0, roe=0.10, net_margin=0.20)
        gap = relative_value_mispricing(30.0, 10.0, first, second, coef=FairRatioCoef(alpha=0.0, eps=1.0))
        self.assertGreater(gap, 0.0)


class CointegrationTests(unittest.TestCase):
    """Validate ADF, Engle-Granger, Johansen, and hedge-ratio recovery."""

    def test_adf_rejects_unit_root_on_white_noise(self) -> None:
        """Stationary noise should be classified as I(0)."""

        rng = np.random.default_rng(1)
        result = adf_test(rng.normal(size=400))
        self.assertTrue(result.stationary)
        self.assertLess(result.pvalue, 0.05)

    def test_adf_does_not_reject_random_walk(self) -> None:
        """A random walk should remain consistent with a unit root."""

        rng = np.random.default_rng(2)
        walk = np.cumsum(rng.normal(size=500))
        result = adf_test(walk)
        self.assertFalse(result.stationary)
        self.assertGreater(result.pvalue, 0.05)

    def test_hedge_ratio_recovers_known_beta(self) -> None:
        """Log-log OLS should recover the simulated cointegrating slope."""

        pair = generate_cointegrated_pair(nobs=1200, beta=1.35, seed=5)
        hedge = estimate_hedge_ratio(pair.prices_a, pair.prices_b)
        self.assertAlmostEqual(hedge.beta, 1.35, delta=0.12)

    def test_engle_granger_finds_synthetic_cointegration(self) -> None:
        """A designed cointegrated pair should pass Engle-Granger."""

        pair = generate_cointegrated_pair(nobs=800, seed=8)
        result = engle_granger(pair.prices_a, pair.prices_b)
        self.assertTrue(result.cointegrated)
        self.assertLess(result.adf.pvalue, 0.05)

    def test_independent_walks_are_not_cointegrated(self) -> None:
        """Two unrelated random walks should fail the cointegration screen."""

        pair = generate_independent_pair(nobs=800, seed=9)
        result = engle_granger(pair.prices_a, pair.prices_b)
        self.assertFalse(result.cointegrated)

    def test_johansen_detects_two_variable_cointegration(self) -> None:
        """Johansen trace should find rank >= 1 on the synthetic pair."""

        pair = generate_cointegrated_pair(nobs=900, seed=4)
        result = johansen_trace(pair.prices_a, pair.prices_b)
        self.assertTrue(result.cointegrated)
        self.assertGreaterEqual(result.rank, 1)


class MeanReversionTests(unittest.TestCase):
    """Validate OU, Hurst, variance-ratio, and z-score helpers."""

    def test_ou_half_life_matches_designed_kappa(self) -> None:
        """OU calibration should recover a 10-day half-life within tolerance."""

        pair = generate_cointegrated_pair(nobs=2000, kappa=np.log(2.0) / 10.0, seed=6)
        hedge = estimate_hedge_ratio(pair.prices_a, pair.prices_b)
        fitted = fit_ou(hedge.residual)
        self.assertAlmostEqual(fitted.half_life, 10.0, delta=4.0)
        self.assertGreater(fitted.kappa, 0.0)

    def test_hurst_of_ou_spread_is_below_half(self) -> None:
        """A mean-reverting spread should have Hurst < 0.5."""

        pair = generate_cointegrated_pair(nobs=1500, seed=12)
        hedge = estimate_hedge_ratio(pair.prices_a, pair.prices_b)
        self.assertLess(hurst_exponent(hedge.residual), 0.5)

    def test_variance_ratio_below_one_for_mean_reverting_increments(self) -> None:
        """OU increments should produce VR(q) < 1."""

        pair = generate_cointegrated_pair(nobs=1200, seed=14)
        hedge = estimate_hedge_ratio(pair.prices_a, pair.prices_b)
        self.assertLess(variance_ratio(np.diff(hedge.residual), period=5), 1.0)

    def test_rolling_zscore_is_standardized(self) -> None:
        """A long z-score series should be roughly zero-mean unit-variance."""

        rng = np.random.default_rng(0)
        series = rng.normal(size=400)
        zscore = rolling_zscore(series, 50)
        finite = zscore[np.isfinite(zscore)]
        self.assertAlmostEqual(float(finite.mean()), 0.0, delta=0.15)
        self.assertAlmostEqual(float(finite.std(ddof=1)), 1.0, delta=0.15)


class StrategyTests(unittest.TestCase):
    """Validate screening, weights, regime breaks, and walk-forward PnL."""

    def test_screen_accepts_cointegrated_pair(self) -> None:
        """The designed broker pair should pass the full screen."""

        pair = generate_cointegrated_pair(nobs=600, seed=21)
        screen = screen_pair(
            pair.prices_a,
            pair.prices_b,
            fundamentals_a=pair.fundamentals_a,
            fundamentals_b=pair.fundamentals_b,
            volumes_a=pair.volumes_a,
            volumes_b=pair.volumes_b,
        )
        self.assertTrue(screen.passed, msg=screen.reasons)
        self.assertGreater(screen.correlation, 0.6)
        self.assertLess(screen.half_life, 60.0)

    def test_screen_rejects_independent_pair(self) -> None:
        """Unrelated airlines with no cointegration should be rejected."""

        pair = generate_independent_pair(nobs=600, seed=22)
        screen = screen_pair(
            pair.prices_a,
            pair.prices_b,
            fundamentals_a=pair.fundamentals_a,
            fundamentals_b=pair.fundamentals_b,
        )
        self.assertFalse(screen.passed)
        self.assertTrue(any("cointegrated" in reason or "correlation" in reason or "distance" in reason for reason in screen.reasons))

    def test_leg_weights_are_dollar_hedged_to_beta(self) -> None:
        """Cointegration weights should long 1 and short β, then normalize."""

        weight_a, weight_b = pair_leg_weights(1.5)
        self.assertAlmostEqual(weight_a, 1.0 / 2.5)
        self.assertAlmostEqual(weight_b, -1.5 / 2.5)

    def test_extreme_zscore_is_a_regime_break_not_an_add(self) -> None:
        """|Z| beyond the stop should be treated as a broken equilibrium."""

        self.assertTrue(detect_regime_break(0.01, 8.0, 8.0, 1.2, 1.2, zscore=4.5, stop_z=4.0))
        self.assertFalse(detect_regime_break(0.01, 8.0, 8.0, 1.2, 1.2, zscore=2.2, stop_z=4.0))

    def test_backtest_is_profitable_on_mean_reverting_dgp(self) -> None:
        """Zero-cost trading of a 10-day OU pair should earn a positive Sharpe."""

        pair = generate_cointegrated_pair(nobs=1260, seed=17)
        config = PairStrategyConfig(
            cost_bps=0.0,
            signal_weights=(1.0, 0.0, 0.0),
            entry_z=1.75,
            max_fundamental_distance=0.2,
        )
        result = run_pair_backtest(
            pair.prices_a,
            pair.prices_b,
            volumes_a=pair.volumes_a,
            volumes_b=pair.volumes_b,
            fundamentals_a=pair.fundamentals_a,
            fundamentals_b=pair.fundamentals_b,
            config=config,
        )
        self.assertGreater(result.n_trades, 3)
        self.assertGreater(result.sharpe, 0.3)
        self.assertGreater(result.total_return, 0.0)

    def test_transaction_costs_reduce_pnl(self) -> None:
        """The same fills with costs must earn no more than the zero-cost book."""

        pair = generate_cointegrated_pair(nobs=900, seed=18)
        kwargs = dict(
            prices_a=pair.prices_a,
            prices_b=pair.prices_b,
            volumes_a=pair.volumes_a,
            volumes_b=pair.volumes_b,
            fundamentals_a=pair.fundamentals_a,
            fundamentals_b=pair.fundamentals_b,
        )
        cheap = run_pair_backtest(config=PairStrategyConfig(cost_bps=0.0, signal_weights=(1.0, 0.0, 0.0)), **kwargs)
        expensive = run_pair_backtest(config=PairStrategyConfig(cost_bps=25.0, signal_weights=(1.0, 0.0, 0.0)), **kwargs)
        self.assertLessEqual(expensive.total_return, cheap.total_return + 1e-12)

    def test_backtest_does_not_use_future_beta(self) -> None:
        """Hedge ratios in a window must come from the preceding formation sample."""

        pair = generate_cointegrated_pair(nobs=700, seed=19, beta=1.2)
        config = PairStrategyConfig(formation_window=252, trade_window=63, signal_weights=(1.0, 0.0, 0.0))
        result = run_pair_backtest(pair.prices_a, pair.prices_b, config=config)
        finite = np.isfinite(result.beta_path)
        self.assertTrue(np.any(finite), msg="walk-forward never estimated a hedge ratio")
        first_live = int(np.flatnonzero(finite)[0])
        self.assertGreaterEqual(first_live, config.formation_window)
        formation_beta = estimate_hedge_ratio(
            pair.prices_a[first_live - config.formation_window : first_live],
            pair.prices_b[first_live - config.formation_window : first_live],
        ).beta
        self.assertAlmostEqual(float(result.beta_path[first_live]), formation_beta, places=10)
        future_end = min(first_live + config.trade_window, pair.prices_a.size)
        future_beta = estimate_hedge_ratio(
            pair.prices_a[first_live:future_end],
            pair.prices_b[first_live:future_end],
        ).beta
        self.assertNotAlmostEqual(float(result.beta_path[first_live]), future_beta, places=4)

    def test_zscore_uses_only_trailing_data(self) -> None:
        """The z-score at t must match a rolling window that ends at t."""

        pair = generate_cointegrated_pair(nobs=400, seed=20)
        hedge = estimate_hedge_ratio(pair.prices_a[:300], pair.prices_b[:300])
        spread = construct_spread(pair.prices_a, pair.prices_b, hedge.alpha, hedge.beta)
        zscore = rolling_zscore(spread, 40)
        window = spread[260:300]
        expected = (spread[299] - window.mean()) / window.std(ddof=1)
        self.assertAlmostEqual(float(zscore[299]), float(expected), places=10)

    def test_regime_break_flattens_after_equilibrium_shift(self) -> None:
        """A beta jump plus dead mean-reversion should eventually force an exit."""

        pair = generate_cointegrated_pair(nobs=900, seed=23, break_at=520, break_beta=0.4)
        config = PairStrategyConfig(
            formation_window=252,
            trade_window=63,
            cost_bps=0.0,
            signal_weights=(1.0, 0.0, 0.0),
            stop_z=3.5,
        )
        result = run_pair_backtest(pair.prices_a, pair.prices_b, config=config)
        post_break = result.regime_break[520:]
        self.assertTrue(np.any(post_break > 0) or np.all(result.positions[700:] == 0.0))

    def test_load_pair_csv_round_trip(self) -> None:
        """CSV helper should round-trip prices and optional volumes."""

        pair = generate_cointegrated_pair(nobs=80, seed=24)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pair.csv"
            lines = ["close_a,close_b,volume_a,volume_b"]
            for price_a, price_b, volume_a, volume_b in zip(
                pair.prices_a, pair.prices_b, pair.volumes_a, pair.volumes_b
            ):
                lines.append(f"{price_a},{price_b},{volume_a},{volume_b}")
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            loaded = load_pair_csv(str(path))
        np.testing.assert_allclose(loaded["prices_a"], pair.prices_a)
        np.testing.assert_allclose(loaded["volumes_b"], pair.volumes_b)


if __name__ == "__main__":
    unittest.main()
