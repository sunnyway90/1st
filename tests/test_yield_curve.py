"""Tests for the bond yield-curve module."""

from __future__ import annotations

import unittest

import numpy as np

from yield_curve import Bond, YieldCurve, bootstrap_zero_curve, solve_yield_to_maturity


class YieldCurveTests(unittest.TestCase):
    """Validate core fixed-income calculations."""

    def test_discount_factor_uses_continuous_compounding(self) -> None:
        """Discount factors should match exp(-r * t)."""

        curve = YieldCurve(np.array([1.0, 2.0]), np.array([0.03, 0.04]), interpolation="linear")

        self.assertAlmostEqual(float(curve.discount_factor(1.0)), float(np.exp(-0.03)))
        self.assertAlmostEqual(float(curve.discount_factor(2.0)), float(np.exp(-0.08)))
        self.assertAlmostEqual(float(curve.zero_rate(1.5)), 0.035)

    def test_bootstrap_reprices_market_bonds(self) -> None:
        """Bootstrapped curve should reprice the input market instruments."""

        source_curve = YieldCurve(
            np.array([0.5, 1.0, 1.5, 2.0]),
            np.array([0.020, 0.023, 0.026, 0.029]),
            interpolation="linear",
        )
        bonds = [
            Bond(maturity=0.5, coupon_rate=0.018, market_price=0.0),
            Bond(maturity=1.0, coupon_rate=0.021, market_price=0.0),
            Bond(maturity=1.5, coupon_rate=0.024, market_price=0.0),
            Bond(maturity=2.0, coupon_rate=0.027, market_price=0.0),
        ]
        market_bonds = [
            Bond(
                maturity=bond.maturity,
                coupon_rate=bond.coupon_rate,
                market_price=source_curve.price_bond(bond),
            )
            for bond in bonds
        ]

        bootstrapped_curve = bootstrap_zero_curve(market_bonds, interpolation="linear")

        for market_bond in market_bonds:
            self.assertIsNotNone(market_bond.market_price)
            self.assertAlmostEqual(
                bootstrapped_curve.price_bond(market_bond),
                float(market_bond.market_price),
                places=10,
            )

    def test_solve_yield_to_maturity_for_par_bond(self) -> None:
        """A par-priced bond's YTM should equal its coupon rate."""

        bond = Bond(maturity=5.0, coupon_rate=0.04, market_price=100.0)

        self.assertAlmostEqual(solve_yield_to_maturity(bond, 100.0), 0.04)

    def test_bootstrap_requires_coupon_date_coverage(self) -> None:
        """Missing earlier coupon-date instruments should raise a clear error."""

        bonds = [Bond(maturity=1.0, coupon_rate=0.04, market_price=100.0)]

        with self.assertRaisesRegex(ValueError, "missing discount factor"):
            bootstrap_zero_curve(bonds)


if __name__ == "__main__":
    unittest.main()
