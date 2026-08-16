"""Hedge ratios, cointegration tests, OU calibration, and spread diagnostics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]

# MacKinnon large-sample ADF critical values for a unit-root test.
ADF_CRITICAL = {
    "n": {0.01: -2.58, 0.05: -1.95, 0.10: -1.61},
    "c": {0.01: -3.43, 0.05: -2.86, 0.10: -2.57},
    "ct": {0.01: -3.96, 0.05: -3.41, 0.10: -3.13},
}

# Engle-Granger residual ADF critical values for two series with a constant.
EG_CRITICAL = {0.01: -3.90, 0.05: -3.34, 0.10: -3.04}

# Osterwald-Lenum 5% trace critical values, constant in VECM, two series.
JOHANSEN_TRACE_5PCT = {0: 15.49, 1: 3.84}


@dataclass(frozen=True)
class OLSResult:
    """Ordinary least squares fit."""

    beta: FloatArray
    residual: FloatArray
    tstat: FloatArray
    r_squared: float
    nobs: int


@dataclass(frozen=True)
class StationarityResult:
    """Unit-root or cointegration residual test."""

    statistic: float
    pvalue: float
    lags: int
    critical_values: dict[float, float]
    stationary: bool

    @property
    def is_stationary(self) -> bool:
        """Alias used by screening code."""

        return self.stationary


@dataclass(frozen=True)
class HedgeRatio:
    """Log-log cointegrating regression ``log P_A = α + β log P_B + ε``."""

    alpha: float
    beta: float
    residual: FloatArray
    r_squared: float


@dataclass(frozen=True)
class EngleGrangerResult:
    """Two-step Engle-Granger cointegration test."""

    hedge: HedgeRatio
    adf: StationarityResult
    cointegrated: bool


@dataclass(frozen=True)
class JohansenResult:
    """Johansen trace test for a two-name system."""

    eigenvalues: FloatArray
    trace_r0: float
    trace_r1: float
    cointegrated: bool
    rank: int


@dataclass(frozen=True)
class OUFit:
    """Ornstein-Uhlenbeck parameters estimated from an AR(1) on the spread."""

    mu: float
    kappa: float
    sigma: float
    half_life: float
    ar_coef: float


def ols(y: FloatArray, x: FloatArray, add_const: bool = True) -> OLSResult:
    """Fit ``y = X β + ε`` with an optional intercept."""

    dependent = np.asarray(y, dtype=np.float64).reshape(-1)
    regressors = np.asarray(x, dtype=np.float64)
    if regressors.ndim == 1:
        regressors = regressors.reshape(-1, 1)
    if dependent.shape[0] != regressors.shape[0]:
        raise ValueError("y and x must have the same number of rows")
    if add_const:
        design = np.column_stack([np.ones(dependent.shape[0]), regressors])
    else:
        design = regressors
    mask = np.isfinite(dependent) & np.all(np.isfinite(design), axis=1)
    dependent = dependent[mask]
    design = design[mask]
    nobs, nparams = design.shape
    if nobs <= nparams:
        raise ValueError("not enough observations for OLS")
    beta, _, _, _ = np.linalg.lstsq(design, dependent, rcond=None)
    residual = dependent - design @ beta
    df = nobs - nparams
    sigma2 = float(np.sum(residual**2) / df)
    gram = design.T @ design
    try:
        cov = sigma2 * np.linalg.inv(gram)
    except np.linalg.LinAlgError as exc:
        raise ValueError("OLS design matrix is singular") from exc
    se = np.sqrt(np.maximum(np.diag(cov), 0.0))
    tstat = np.divide(beta, se, out=np.full_like(beta, np.nan), where=se > 0)
    sst = float(np.sum((dependent - dependent.mean()) ** 2))
    r_squared = 1.0 - float(np.sum(residual**2)) / sst if sst > 0 else np.nan
    return OLSResult(
        beta=np.asarray(beta, dtype=np.float64),
        residual=np.asarray(residual, dtype=np.float64),
        tstat=np.asarray(tstat, dtype=np.float64),
        r_squared=float(r_squared),
        nobs=int(nobs),
    )


def log_prices(prices: FloatArray) -> FloatArray:
    """Natural log of strictly positive prices."""

    values = np.asarray(prices, dtype=np.float64)
    if np.any(values <= 0.0):
        raise ValueError("prices must be positive")
    return np.log(values)


def simple_returns(prices: FloatArray) -> FloatArray:
    """Close-to-close log returns."""

    logs = log_prices(prices)
    return np.diff(logs)


def return_correlation(prices_a: FloatArray, prices_b: FloatArray) -> float:
    """Pearson correlation of log returns."""

    returns_a = simple_returns(prices_a)
    returns_b = simple_returns(prices_b)
    if returns_a.size != returns_b.size:
        raise ValueError("price series must have the same length")
    mask = np.isfinite(returns_a) & np.isfinite(returns_b)
    if int(np.count_nonzero(mask)) < 3:
        return np.nan
    return float(np.corrcoef(returns_a[mask], returns_b[mask])[0, 1])


def estimate_hedge_ratio(prices_a: FloatArray, prices_b: FloatArray) -> HedgeRatio:
    """Estimate ``β`` from ``log P_A = α + β log P_B + ε``."""

    fitted = ols(log_prices(prices_a), log_prices(prices_b), add_const=True)
    return HedgeRatio(
        alpha=float(fitted.beta[0]),
        beta=float(fitted.beta[1]),
        residual=fitted.residual,
        r_squared=fitted.r_squared,
    )


def construct_spread(prices_a: FloatArray, prices_b: FloatArray, alpha: float, beta: float) -> FloatArray:
    """Return ``S_t = log P_A - α - β log P_B``."""

    return log_prices(prices_a) - alpha - beta * log_prices(prices_b)


def _pvalue_from_critical(statistic: float, critical: dict[float, float]) -> float:
    """Piecewise-linear p-value from a handful of critical-value anchors."""

    anchors = sorted(((cv, p) for p, cv in critical.items()), key=lambda item: item[0])
    points = [(-8.0, 1e-4)] + anchors + [(0.5, 0.95)]
    if statistic <= points[0][0]:
        return points[0][1]
    if statistic >= points[-1][0]:
        return points[-1][1]
    for (x0, p0), (x1, p1) in zip(points, points[1:]):
        if x0 <= statistic <= x1:
            weight = (statistic - x0) / (x1 - x0) if x1 != x0 else 0.0
            return float(p0 + weight * (p1 - p0))
    return 1.0


def _adf_regression(series: FloatArray, lags: int, regression: str) -> tuple[float, float]:
    """Return ``(t-stat on lagged level, AIC)`` for one ADF specification."""

    y = np.asarray(series, dtype=np.float64)
    delta = np.diff(y)
    lagged_level = y[:-1]
    start = lags
    dependent = delta[start:]
    columns = [lagged_level[start:]]
    if regression in {"c", "ct"}:
        columns.append(np.ones(dependent.shape[0]))
    if regression == "ct":
        columns.append(np.arange(start + 1, start + 1 + dependent.shape[0], dtype=np.float64))
    for lag in range(1, lags + 1):
        columns.append(delta[start - lag : delta.shape[0] - lag])
    design = np.column_stack(columns)
    if dependent.shape[0] <= design.shape[1]:
        return np.nan, np.inf
    beta, _, _, _ = np.linalg.lstsq(design, dependent, rcond=None)
    residual = dependent - design @ beta
    df = dependent.shape[0] - design.shape[1]
    if df <= 0:
        return np.nan, np.inf
    sigma2 = float(np.sum(residual**2) / df)
    try:
        cov = sigma2 * np.linalg.inv(design.T @ design)
    except np.linalg.LinAlgError:
        return np.nan, np.inf
    se_gamma = float(np.sqrt(max(cov[0, 0], 0.0)))
    if se_gamma <= 0.0:
        return np.nan, np.inf
    statistic = float(beta[0] / se_gamma)
    rss = float(np.mean(residual**2))
    aic = dependent.shape[0] * np.log(max(rss, 1e-18)) + 2.0 * design.shape[1]
    return statistic, aic


def adf_test(
    series: FloatArray,
    max_lags: int | None = None,
    regression: str = "c",
    autolag: bool = True,
) -> StationarityResult:
    """Augmented Dickey-Fuller test with optional AIC lag selection."""

    if regression not in ADF_CRITICAL:
        raise ValueError("regression must be one of 'n', 'c', or 'ct'")
    values = np.asarray(series, dtype=np.float64)
    values = values[np.isfinite(values)]
    nobs = values.size
    if nobs < 20:
        raise ValueError("ADF test needs at least 20 observations")
    if max_lags is None:
        max_lags = int(np.floor(12.0 * (nobs / 100.0) ** 0.25))
    max_lags = int(max(0, min(max_lags, nobs // 4)))
    if autolag:
        best = (np.inf, np.nan, 0)
        for lags in range(0, max_lags + 1):
            statistic, aic = _adf_regression(values, lags, regression)
            if aic < best[0]:
                best = (aic, statistic, lags)
        statistic = float(best[1])
        chosen_lags = int(best[2])
    else:
        statistic, _ = _adf_regression(values, max_lags, regression)
        chosen_lags = max_lags
    critical = dict(ADF_CRITICAL[regression])
    pvalue = _pvalue_from_critical(statistic, critical)
    return StationarityResult(
        statistic=float(statistic),
        pvalue=float(pvalue),
        lags=chosen_lags,
        critical_values=critical,
        stationary=bool(statistic < critical[0.05]),
    )


def engle_granger(prices_a: FloatArray, prices_b: FloatArray, max_lags: int | None = None) -> EngleGrangerResult:
    """Engle-Granger two-step cointegration test on log prices."""

    hedge = estimate_hedge_ratio(prices_a, prices_b)
    adf = adf_test(hedge.residual, max_lags=max_lags, regression="n", autolag=True)
    pvalue = _pvalue_from_critical(adf.statistic, EG_CRITICAL)
    cointegrated = bool(adf.statistic < EG_CRITICAL[0.05])
    adjusted = StationarityResult(
        statistic=adf.statistic,
        pvalue=float(pvalue),
        lags=adf.lags,
        critical_values=dict(EG_CRITICAL),
        stationary=cointegrated,
    )
    return EngleGrangerResult(hedge=hedge, adf=adjusted, cointegrated=cointegrated)


def johansen_trace(prices_a: FloatArray, prices_b: FloatArray, lags: int = 1) -> JohansenResult:
    """Two-variable Johansen trace test on log prices with a constant."""

    if lags < 0:
        raise ValueError("lags must be non-negative")
    levels = np.column_stack([log_prices(prices_a), log_prices(prices_b)])
    delta = np.diff(levels, axis=0)
    lagged = levels[:-1]
    start = lags
    z0 = delta[start:]
    z1 = lagged[start:]
    extra: list[FloatArray] = [np.ones(z0.shape[0])]
    for lag in range(1, lags + 1):
        extra.append(delta[start - lag : delta.shape[0] - lag])
    z2 = np.column_stack(extra) if extra else np.ones((z0.shape[0], 1))

    def _residualize(target: FloatArray, controls: FloatArray) -> FloatArray:
        fit, _, _, _ = np.linalg.lstsq(controls, target, rcond=None)
        return target - controls @ fit

    r0 = _residualize(z0, z2)
    r1 = _residualize(z1, z2)
    nobs = r0.shape[0]
    s00 = (r0.T @ r0) / nobs
    s11 = (r1.T @ r1) / nobs
    s01 = (r0.T @ r1) / nobs
    s10 = s01.T
    try:
        middle = s10 @ np.linalg.solve(s00, s01)
        matrix = np.linalg.solve(s11, middle)
    except np.linalg.LinAlgError as exc:
        raise ValueError("Johansen moment matrices are singular") from exc
    eigenvalues = np.sort(np.real(np.linalg.eigvals(matrix)))[::-1]
    eigenvalues = np.clip(eigenvalues, 0.0, 0.999)
    trace_r0 = float(-nobs * np.sum(np.log(1.0 - eigenvalues)))
    trace_r1 = float(-nobs * np.log(1.0 - eigenvalues[1]))
    rank = 0
    if trace_r0 > JOHANSEN_TRACE_5PCT[0]:
        rank = 1
        if trace_r1 > JOHANSEN_TRACE_5PCT[1]:
            rank = 2
    return JohansenResult(
        eigenvalues=np.asarray(eigenvalues, dtype=np.float64),
        trace_r0=trace_r0,
        trace_r1=trace_r1,
        cointegrated=rank >= 1,
        rank=int(rank),
    )


def fit_ou(spread: FloatArray, dt: float = 1.0) -> OUFit:
    """Estimate an Ornstein-Uhlenbeck process from discrete spread observations.

    The AR(1) ``S_t = a + b S_{t-1} + ε`` maps to
    ``κ = -log(b)/Δt``, ``μ = a / (1-b)``, and
    ``σ = std(ε) * sqrt(2κ / (1 - exp(-2κΔt)))``.
    """

    values = np.asarray(spread, dtype=np.float64)
    values = values[np.isfinite(values)]
    if values.size < 10:
        raise ValueError("OU calibration needs at least 10 observations")
    fitted = ols(values[1:], values[:-1], add_const=True)
    intercept = float(fitted.beta[0])
    ar_coef = float(fitted.beta[1])
    if ar_coef <= 0.0 or ar_coef >= 1.0:
        return OUFit(mu=float(values.mean()), kappa=np.nan, sigma=np.nan, half_life=np.inf, ar_coef=ar_coef)
    kappa = float(-np.log(ar_coef) / dt)
    mu = float(intercept / (1.0 - ar_coef))
    resid_std = float(np.std(fitted.residual, ddof=2))
    denom = 1.0 - np.exp(-2.0 * kappa * dt)
    sigma = float(resid_std * np.sqrt(2.0 * kappa / denom)) if denom > 0.0 else np.nan
    half_life = float(np.log(2.0) / kappa) if kappa > 0.0 else np.inf
    return OUFit(mu=mu, kappa=kappa, sigma=sigma, half_life=half_life, ar_coef=ar_coef)


def hurst_exponent(series: FloatArray, min_lag: int = 2, max_lag: int | None = None) -> float:
    """Lagged-difference Hurst exponent of a spread or price series.

    ``std(X_{t+lag} - X_t) ~ lag^H``. A random walk has ``H ≈ 0.5``;
    a mean-reverting spread saturates and yields ``H < 0.5``. This is the
    estimator commonly used to screen pairs, not R/S on the raw levels.
    """

    values = np.asarray(series, dtype=np.float64)
    values = values[np.isfinite(values)]
    nobs = values.size
    if nobs < 32:
        raise ValueError("Hurst exponent needs at least 32 observations")
    if max_lag is None:
        max_lag = min(80, nobs // 3)
    max_lag = int(max(min_lag + 4, max_lag))
    lags = np.unique(np.logspace(np.log10(min_lag), np.log10(max_lag), 18).astype(int))
    used: list[int] = []
    scales: list[float] = []
    for lag in lags:
        if lag < min_lag or lag >= nobs // 2:
            continue
        delta = values[int(lag) :] - values[: -int(lag)]
        if delta.size < 8:
            continue
        scale = float(np.std(delta, ddof=1))
        if scale > 0.0:
            used.append(int(lag))
            scales.append(scale)
    if len(used) < 3:
        return np.nan
    slope, _ = np.polyfit(np.log(np.asarray(used, dtype=np.float64)), np.log(np.asarray(scales, dtype=np.float64)), 1)
    return float(slope)


def variance_ratio(returns: FloatArray, period: int = 2) -> float:
    """Overlapping Lo-MacKinlay variance ratio of horizon ``period``.

    Mean-reverting increments produce ``VR(q) < 1``.
    """

    if period < 2:
        raise ValueError("period must be at least 2")
    values = np.asarray(returns, dtype=np.float64)
    values = values[np.isfinite(values)]
    nobs = values.size
    if nobs <= period + 2:
        raise ValueError("not enough observations for the variance-ratio test")
    mean = float(values.mean())
    var_1 = float(np.sum((values - mean) ** 2) / (nobs - 1))
    if var_1 <= 0.0:
        return np.nan
    overlapping = np.convolve(values, np.ones(period, dtype=np.float64), mode="valid")
    var_q = float(np.sum((overlapping - period * mean) ** 2) / (overlapping.size - 1))
    return float(var_q / (period * var_1))


def rolling_mean(series: FloatArray, window: int) -> FloatArray:
    """Trailing moving average; a window is defined only when it is fully finite."""

    if window <= 0:
        raise ValueError("window must be positive")
    values = np.asarray(series, dtype=np.float64)
    nobs = values.size
    out = np.full(nobs, np.nan, dtype=np.float64)
    if nobs < window:
        return out
    filled = np.nan_to_num(values, nan=0.0)
    finite = np.isfinite(values).astype(np.float64)
    sums = np.cumsum(filled)
    counts = np.cumsum(finite)
    window_sum = np.empty(nobs, dtype=np.float64)
    window_count = np.empty(nobs, dtype=np.float64)
    window_sum[: window - 1] = np.nan
    window_count[: window - 1] = np.nan
    window_sum[window - 1] = sums[window - 1]
    window_count[window - 1] = counts[window - 1]
    window_sum[window:] = sums[window:] - sums[:-window]
    window_count[window:] = counts[window:] - counts[:-window]
    valid = window_count >= window
    np.divide(window_sum, window_count, out=out, where=valid)
    return out


def rolling_std(series: FloatArray, window: int, ddof: int = 1) -> FloatArray:
    """Trailing standard deviation with NaNs until the window is full."""

    mean = rolling_mean(series, window)
    mean_sq = rolling_mean(np.asarray(series, dtype=np.float64) ** 2, window)
    variance = mean_sq - mean**2
    if ddof:
        variance = variance * window / max(window - ddof, 1)
    return np.sqrt(np.maximum(variance, 0.0))


def rolling_zscore(series: FloatArray, window: int) -> FloatArray:
    """``(S_t - MA_n(S_t)) / STD_n(S_t)``."""

    values = np.asarray(series, dtype=np.float64)
    mean = rolling_mean(values, window)
    scale = rolling_std(values, window)
    return np.divide(values - mean, scale, out=np.full_like(values, np.nan), where=scale > 1e-12)


def realized_volatility(prices: FloatArray, window: int) -> FloatArray:
    """Trailing standard deviation of log returns, aligned to price dates."""

    returns = simple_returns(prices)
    vol = rolling_std(returns, window)
    aligned = np.full(np.asarray(prices).shape[0], np.nan, dtype=np.float64)
    aligned[1:] = vol
    return aligned
