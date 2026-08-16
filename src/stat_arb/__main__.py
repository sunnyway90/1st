"""Demo: fundamental screening, cointegration, OU half-life, and pair backtest."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from stat_arb.simulate import generate_cointegrated_pair, generate_independent_pair
from stat_arb.spread import estimate_hedge_ratio, rolling_zscore
from stat_arb.strategy import PairStrategyConfig, run_pair_backtest, screen_pair


def _print_screen(title: str, screen) -> None:
    print(title)
    print("-" * len(title))
    print(f"passed:                 {screen.passed}")
    print(f"return correlation:     {screen.correlation:.3f}")
    print(f"hedge ratio β:          {screen.hedge_beta:.3f}")
    print(f"Engle-Granger p-value:  {screen.adf_pvalue:.4f}")
    print(f"Johansen cointegrated:  {screen.johansen_cointegrated}")
    print(f"OU half-life (days):    {screen.half_life:.2f}")
    print(f"Hurst exponent:         {screen.hurst:.3f}")
    print(f"variance ratio q=5:     {screen.variance_ratio:.3f}")
    print(f"fundamental distance:   {screen.fundamental_distance:.4f}")
    print(f"relative-value gap:     {screen.mispricing:.4f}")
    if screen.reasons:
        print("reject reasons:")
        for reason in screen.reasons:
            print(f"  - {reason}")
    print()


def _plot_backtest(pair, result, output_path: Path) -> Figure:
    hedge = estimate_hedge_ratio(pair.prices_a, pair.prices_b)
    spread = result.spread.copy()
    missing = ~np.isfinite(spread)
    if np.any(missing):
        full = np.log(pair.prices_a) - hedge.alpha - hedge.beta * np.log(pair.prices_b)
        spread[missing] = full[missing]
    zscore = result.zscore.copy()
    missing_z = ~np.isfinite(zscore)
    if np.any(missing_z):
        zscore[missing_z] = rolling_zscore(spread, 60)[missing_z]

    figure, axes = plt.subplots(2, 2, figsize=(11, 8), constrained_layout=True)
    axes[0, 0].plot(pair.prices_a / pair.prices_a[0], label=pair.fundamentals_a.ticker)
    axes[0, 0].plot(pair.prices_b / pair.prices_b[0], label=pair.fundamentals_b.ticker)
    axes[0, 0].set_title("Normalized prices")
    axes[0, 0].legend(frameon=False)

    axes[0, 1].plot(spread, color="C2", linewidth=1.0)
    axes[0, 1].axhline(0.0, color="black", linewidth=0.8)
    axes[0, 1].set_title("Cointegration spread")

    axes[1, 0].plot(zscore, color="C3", linewidth=1.0)
    axes[1, 0].axhline(2.0, color="black", linestyle="--", linewidth=0.8)
    axes[1, 0].axhline(-2.0, color="black", linestyle="--", linewidth=0.8)
    axes[1, 0].axhline(0.5, color="gray", linestyle=":", linewidth=0.8)
    axes[1, 0].axhline(-0.5, color="gray", linestyle=":", linewidth=0.8)
    axes[1, 0].set_title("Spread z-score")

    axes[1, 1].plot(result.equity, color="C0")
    axes[1, 1].set_title("Walk-forward equity (net of costs)")
    for axis in axes.ravel():
        axis.set_xlabel("day")
        axis.grid(True, alpha=0.25)
    figure.savefig(output_path, dpi=150)
    return figure


def main() -> None:
    """Run the statistical-arbitrage demo on a synthetic cointegrated pair."""

    parser = argparse.ArgumentParser(description="Fundamental + cointegration pairs-trading demo")
    parser.add_argument("--output", type=Path, default=Path("stat_arb_demo.png"), help="chart path")
    parser.add_argument("--seed", type=int, default=7, help="simulation seed")
    parser.add_argument("--nobs", type=int, default=1008, help="number of simulated sessions")
    args = parser.parse_args()

    pair = generate_cointegrated_pair(nobs=args.nobs, seed=args.seed)
    decoy = generate_independent_pair(nobs=args.nobs, seed=args.seed + 13)
    config = PairStrategyConfig(cost_bps=8.0, signal_weights=(1.0, 0.1, 0.05))

    print("True DGP")
    print("--------")
    print(f"β:                      {pair.true_beta:.3f}")
    print(f"half-life:              {pair.true_half_life:.2f} days")
    print(f"industry:               {pair.fundamentals_a.industry}")
    print()

    _print_screen("Screen: cointegrated pair AAA/BBB", screen_pair(
        pair.prices_a,
        pair.prices_b,
        fundamentals_a=pair.fundamentals_a,
        fundamentals_b=pair.fundamentals_b,
        volumes_a=pair.volumes_a,
        volumes_b=pair.volumes_b,
        config=config,
    ))
    _print_screen("Screen: independent pair XXX/YYY", screen_pair(
        decoy.prices_a,
        decoy.prices_b,
        fundamentals_a=decoy.fundamentals_a,
        fundamentals_b=decoy.fundamentals_b,
        volumes_a=decoy.volumes_a,
        volumes_b=decoy.volumes_b,
        config=config,
    ))

    result = run_pair_backtest(
        pair.prices_a,
        pair.prices_b,
        volumes_a=pair.volumes_a,
        volumes_b=pair.volumes_b,
        fundamentals_a=pair.fundamentals_a,
        fundamentals_b=pair.fundamentals_b,
        config=config,
    )
    print("Walk-forward backtest AAA/BBB")
    print("-----------------------------")
    print(f"trades:                 {result.n_trades}")
    print(f"total return:           {result.total_return:.4f}")
    print(f"annualized Sharpe:      {result.sharpe:.3f}")
    print(f"hit rate:               {result.hit_rate:.3f}")
    print(f"gross turnover:         {result.turnover:.3f}")
    print(f"regime-break days:      {int(np.count_nonzero(result.regime_break))}")
    if result.notes:
        print(f"skipped windows:        {len(result.notes)}")

    figure = _plot_backtest(pair, result, args.output)
    plt.close(figure)
    print(f"Saved chart to {args.output}")


if __name__ == "__main__":
    main()
