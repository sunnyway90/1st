"""Demo entry point for the bond yield-curve module."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from yield_curve.core import Bond, YieldCurve, bootstrap_zero_curve, solve_yield_to_maturity


def main() -> None:
    """Run a demonstration of bootstrapping and plotting a bond yield curve."""

    output_path = Path("yield_curve_demo.png")
    coupon_frequency = 2
    maturities = np.arange(0.5, 5.5, 0.5)
    true_zero_rates = 0.018 + 0.010 * (1.0 - np.exp(-maturities / 2.0))
    reference_curve = YieldCurve(maturities, true_zero_rates)

    market_bonds: list[Bond] = []
    for maturity in maturities:
        coupon_rate = 0.018 + 0.0025 * maturity
        bond = Bond(
            maturity=float(maturity),
            coupon_rate=float(coupon_rate),
            coupon_frequency=coupon_frequency,
        )
        market_price = reference_curve.price_bond(bond)
        market_bonds.append(
            Bond(
                maturity=bond.maturity,
                coupon_rate=bond.coupon_rate,
                coupon_frequency=bond.coupon_frequency,
                market_price=market_price,
            )
        )

    bootstrapped_curve = bootstrap_zero_curve(market_bonds)
    sample_bond = Bond(maturity=3.0, coupon_rate=0.0275, coupon_frequency=coupon_frequency)
    sample_price = bootstrapped_curve.price_bond(sample_bond)
    sample_ytm = solve_yield_to_maturity(sample_bond, sample_price)
    one_year_forward = bootstrapped_curve.forward_rate(1.0, 2.0)

    print("Bootstrapped zero curve")
    print("------------------------")
    for maturity, zero_rate in zip(bootstrapped_curve.maturities, bootstrapped_curve.zero_rates):
        print(f"{maturity:>4.1f}y: {zero_rate * 100:>6.3f}%")
    print()
    print(f"Sample 3.0y bond price: {sample_price:.4f}")
    print(f"Sample 3.0y bond YTM:   {sample_ytm * 100:.3f}%")
    print(f"1y-2y forward rate:     {one_year_forward * 100:.3f}%")

    figure = bootstrapped_curve.plot(show=False)
    figure.savefig(output_path, dpi=150)
    plt.close(figure)
    print(f"Saved chart to {output_path}")


if __name__ == "__main__":
    main()
