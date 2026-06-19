"""Bond cash-flow, yield-curve, and bootstrapping utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from numpy.typing import NDArray
from scipy.interpolate import PchipInterpolator
from scipy.optimize import brentq

FloatArray = NDArray[np.float64]
InterpolationMethod = Literal["linear", "pchip"]


@dataclass(frozen=True)
class Bond:
    """A fixed-rate bond described by annualized coupon terms.

    Args:
        maturity: Final maturity in years.
        coupon_rate: Annual coupon rate as a decimal, for example ``0.035``.
        face_value: Principal repaid at maturity.
        coupon_frequency: Number of coupon payments per year.
        market_price: Optional observed clean price used for bootstrapping.
    """

    maturity: float
    coupon_rate: float
    face_value: float = 100.0
    coupon_frequency: int = 2
    market_price: float | None = None

    def __post_init__(self) -> None:
        """Validate bond terms."""

        if self.maturity <= 0:
            raise ValueError("maturity must be positive")
        if self.coupon_rate < 0:
            raise ValueError("coupon_rate cannot be negative")
        if self.face_value <= 0:
            raise ValueError("face_value must be positive")
        if self.coupon_frequency <= 0:
            raise ValueError("coupon_frequency must be positive")
        periods = self.maturity * self.coupon_frequency
        if not np.isclose(periods, round(periods), atol=1e-10):
            raise ValueError("maturity must align with coupon_frequency")

    def cash_flows(self) -> tuple[FloatArray, FloatArray]:
        """Return payment times and cash-flow amounts.

        Returns:
            A tuple of ``(times, amounts)`` where times are measured in years.
        """

        periods = int(round(self.maturity * self.coupon_frequency))
        times = np.arange(1, periods + 1, dtype=np.float64) / self.coupon_frequency
        coupon = self.face_value * self.coupon_rate / self.coupon_frequency
        amounts = np.full(periods, coupon, dtype=np.float64)
        amounts[-1] += self.face_value
        return times, amounts


@dataclass(frozen=True)
class YieldCurve:
    """Continuously compounded zero-rate curve.

    Args:
        maturities: Curve pillar maturities in years.
        zero_rates: Continuously compounded annual zero rates.
        interpolation: Interpolation method for rates between pillars.
    """

    maturities: FloatArray
    zero_rates: FloatArray
    interpolation: InterpolationMethod = "pchip"

    def __post_init__(self) -> None:
        """Validate curve pillars and normalize array storage."""

        maturities = np.asarray(self.maturities, dtype=np.float64)
        zero_rates = np.asarray(self.zero_rates, dtype=np.float64)
        if maturities.ndim != 1 or zero_rates.ndim != 1:
            raise ValueError("maturities and zero_rates must be one-dimensional")
        if maturities.size == 0:
            raise ValueError("at least one curve pillar is required")
        if maturities.size != zero_rates.size:
            raise ValueError("maturities and zero_rates must have the same length")
        if np.any(maturities <= 0):
            raise ValueError("maturities must be positive")
        if np.any(np.diff(maturities) <= 0):
            raise ValueError("maturities must be strictly increasing")
        if self.interpolation not in ("linear", "pchip"):
            raise ValueError("interpolation must be 'linear' or 'pchip'")
        object.__setattr__(self, "maturities", maturities)
        object.__setattr__(self, "zero_rates", zero_rates)

    def zero_rate(self, times: float | Iterable[float] | FloatArray) -> float | FloatArray:
        """Interpolate continuously compounded zero rates.

        Args:
            times: One or more maturities in years.

        Returns:
            A scalar rate for scalar input, otherwise a ``numpy`` array.
        """

        scalar_input = np.isscalar(times)
        query_times = np.asarray(times, dtype=np.float64)
        if np.any(query_times <= 0):
            raise ValueError("times must be positive")

        if self.maturities.size == 1:
            rates = np.full_like(query_times, self.zero_rates[0], dtype=np.float64)
        elif self.interpolation == "linear":
            rates = np.interp(
                query_times,
                self.maturities,
                self.zero_rates,
                left=self.zero_rates[0],
                right=self.zero_rates[-1],
            )
        else:
            interpolator = PchipInterpolator(self.maturities, self.zero_rates, extrapolate=True)
            rates = np.asarray(interpolator(query_times), dtype=np.float64)

        if scalar_input:
            return float(rates)
        return rates

    def discount_factor(self, times: float | Iterable[float] | FloatArray) -> float | FloatArray:
        """Calculate discount factors from continuously compounded zero rates.

        Args:
            times: One or more maturities in years.

        Returns:
            A scalar discount factor for scalar input, otherwise a ``numpy`` array.
        """

        scalar_input = np.isscalar(times)
        query_times = np.asarray(times, dtype=np.float64)
        rates = np.asarray(self.zero_rate(query_times), dtype=np.float64)
        discounts = np.exp(-rates * query_times)
        if scalar_input:
            return float(discounts)
        return discounts

    def price_bond(self, bond: Bond) -> float:
        """Price a fixed-rate bond by discounting each cash flow.

        Args:
            bond: Bond to price.

        Returns:
            Present value of the bond.
        """

        times, amounts = bond.cash_flows()
        discounts = np.asarray(self.discount_factor(times), dtype=np.float64)
        return float(np.sum(amounts * discounts))

    def forward_rate(self, start: float, end: float) -> float:
        """Calculate the continuously compounded forward rate between two dates.

        Args:
            start: Forward period start in years.
            end: Forward period end in years.

        Returns:
            Annualized continuously compounded forward rate.
        """

        if start <= 0 or end <= 0:
            raise ValueError("start and end must be positive")
        if end <= start:
            raise ValueError("end must be greater than start")
        start_discount = float(self.discount_factor(start))
        end_discount = float(self.discount_factor(end))
        return float(np.log(start_discount / end_discount) / (end - start))

    def plot(self, *, title: str = "Bootstrapped Zero Yield Curve", show: bool = True) -> Figure:
        """Plot the curve with ``matplotlib``.

        Args:
            title: Chart title.
            show: Whether to display the figure immediately.

        Returns:
            The created ``matplotlib`` figure.
        """

        dense_maturities = np.linspace(self.maturities[0], self.maturities[-1], 200)
        dense_rates = np.asarray(self.zero_rate(dense_maturities), dtype=np.float64)

        figure, axis = plt.subplots(figsize=(9, 5))
        axis.plot(dense_maturities, dense_rates * 100.0, label="Interpolated zero rate")
        axis.scatter(self.maturities, self.zero_rates * 100.0, color="tab:red", label="Pillars")
        axis.set_title(title)
        axis.set_xlabel("Maturity (years)")
        axis.set_ylabel("Continuously compounded zero rate (%)")
        axis.grid(True, alpha=0.3)
        axis.legend()
        figure.tight_layout()
        if show:
            plt.show()
        return figure


def bootstrap_zero_curve(
    bonds: Iterable[Bond],
    *,
    interpolation: InterpolationMethod = "pchip",
) -> YieldCurve:
    """Bootstrap a zero curve from fixed-rate bonds.

    Each bond must include ``market_price``. Coupon-bond maturities should cover
    every earlier coupon date needed by later instruments, which keeps the
    bootstrap algebra explicit and avoids circular interpolation assumptions.

    Args:
        bonds: Market instruments sorted automatically by maturity.
        interpolation: Interpolation method used by the returned curve.

    Returns:
        A bootstrapped continuously compounded zero-rate curve.
    """

    sorted_bonds = sorted(bonds, key=lambda bond: bond.maturity)
    if not sorted_bonds:
        raise ValueError("at least one bond is required")

    known_discounts: dict[float, float] = {}
    maturities: list[float] = []
    zero_rates: list[float] = []

    for bond in sorted_bonds:
        if bond.market_price is None:
            raise ValueError("all bonds must include market_price")

        times, amounts = bond.cash_flows()
        maturity = float(times[-1])
        earlier_value = 0.0
        for time, amount in zip(times[:-1], amounts[:-1]):
            earlier_value += float(amount) * _known_discount_factor(known_discounts, float(time))

        final_amount = float(amounts[-1])
        final_discount = (bond.market_price - earlier_value) / final_amount
        if final_discount <= 0:
            raise ValueError(f"bond maturity {bond.maturity:g} implies a non-positive discount factor")

        known_discounts[_normalize_time(maturity)] = final_discount
        maturities.append(maturity)
        zero_rates.append(-np.log(final_discount) / maturity)

    return YieldCurve(np.array(maturities), np.array(zero_rates), interpolation=interpolation)


def solve_yield_to_maturity(
    bond: Bond,
    price: float,
    *,
    lower_bound: float = -0.95,
    upper_bound: float = 1.00,
) -> float:
    """Solve a bond's nominal annual yield to maturity.

    Args:
        bond: Fixed-rate bond to evaluate.
        price: Observed bond price.
        lower_bound: Lower search bound for the nominal annual yield.
        upper_bound: Upper search bound for the nominal annual yield.

    Returns:
        Nominal annual yield compounded at ``bond.coupon_frequency``.
    """

    if price <= 0:
        raise ValueError("price must be positive")
    if lower_bound >= upper_bound:
        raise ValueError("lower_bound must be less than upper_bound")

    times, amounts = bond.cash_flows()

    def price_difference(yield_rate: float) -> float:
        period_rate = yield_rate / bond.coupon_frequency
        if period_rate <= -1:
            return float("inf")
        discount_powers = times * bond.coupon_frequency
        model_price = np.sum(amounts / np.power(1.0 + period_rate, discount_powers))
        return float(model_price - price)

    return float(brentq(price_difference, lower_bound, upper_bound))


def _known_discount_factor(discounts: dict[float, float], time: float) -> float:
    """Fetch a bootstrapped discount factor for an exact coupon date."""

    normalized = _normalize_time(time)
    try:
        return discounts[normalized]
    except KeyError as exc:
        raise ValueError(
            "missing discount factor for coupon date "
            f"{time:g}; provide a market bond maturing at that date"
        ) from exc


def _normalize_time(time: float) -> float:
    """Normalize floating point coupon dates for dictionary lookups."""

    return round(float(time), 10)
