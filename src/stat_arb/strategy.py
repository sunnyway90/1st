"""Pair screening, trading signals, regime-break detection, and walk-forward backtests."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from stat_arb.fundamentals import (
    FairRatioCoef,
    FundamentalSnapshot,
    fundamental_distance,
    relative_value_mispricing,
    same_industry,
)
from stat_arb.spread import (
    OUFit,
    construct_spread,
    engle_granger,
    estimate_hedge_ratio,
    fit_ou,
    hurst_exponent,
    johansen_trace,
    realized_volatility,
    return_correlation,
    rolling_std,
    rolling_zscore,
    simple_returns,
    variance_ratio,
)

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class PairStrategyConfig:
    """Thresholds for screening, signalling, and risk control.

    Args:
        formation_window: Lookback used to estimate β and quality metrics.
        trade_window: Days to trade before the hedge ratio is re-estimated.
        z_window: Rolling window for the spread z-score.
        vol_window: Rolling window for realized-volatility features.
        entry_z: Open when ``|Z|`` exceeds this value.
        exit_z: Flatten when ``|Z|`` falls back inside this band.
        stop_z: Flatten and flag a regime break when ``|Z|`` exceeds this.
        max_holding_days: Flatten after this many days in a trade.
        min_correlation: Minimum formation-window return correlation.
        max_adf_pvalue: Maximum Engle-Granger residual p-value.
        max_half_life: Maximum OU half-life accepted at formation.
        max_hurst: Maximum Hurst exponent accepted at formation.
        min_adv: Minimum average dollar volume for each leg.
        max_bid_ask_bps: Maximum quoted spread for each leg.
        max_fundamental_distance: Maximum fundamental L1 distance.
        require_same_industry: Reject pairs from different industries.
        cost_bps: One-way cost charged on ``|Δw_A| + |Δw_B|``.
        target_daily_vol: Scale positions toward this daily spread volatility.
        max_leverage: Cap on the volatility-scaling multiplier.
        signal_weights: Weights on price, volume, and volatility z-scores.
        strict_walkforward_screen: If True, re-apply the full pair screen
            on every formation window. The default only stops a live pair
            when correlation, half-life, or Hurst indicate a broken relationship.
    """

    formation_window: int = 252
    trade_window: int = 63
    z_window: int = 60
    vol_window: int = 20
    entry_z: float = 2.0
    exit_z: float = 0.5
    stop_z: float = 4.0
    max_holding_days: int = 40
    min_correlation: float = 0.6
    max_adf_pvalue: float = 0.05
    max_half_life: float = 60.0
    max_hurst: float = 0.5
    min_adv: float = 1e6
    max_bid_ask_bps: float = 20.0
    max_fundamental_distance: float = 0.15
    require_same_industry: bool = True
    cost_bps: float = 10.0
    target_daily_vol: float = 0.01
    max_leverage: float = 3.0
    signal_weights: tuple[float, float, float] = (1.0, 0.15, 0.10)
    strict_walkforward_screen: bool = False


@dataclass(frozen=True)
class PairScreenResult:
    """Diagnostics produced by the statistical-plus-fundamental screen."""

    passed: bool
    reasons: tuple[str, ...]
    correlation: float
    hedge_alpha: float
    hedge_beta: float
    adf_pvalue: float
    johansen_cointegrated: bool
    half_life: float
    hurst: float
    variance_ratio: float
    fundamental_distance: float
    mispricing: float
    ou: OUFit | None


@dataclass
class BacktestResult:
    """Walk-forward pair backtest output."""

    positions: FloatArray
    weights_a: FloatArray
    weights_b: FloatArray
    spread: FloatArray
    zscore: FloatArray
    pnl: FloatArray
    equity: FloatArray
    beta_path: FloatArray
    regime_break: FloatArray
    n_trades: int
    sharpe: float
    total_return: float
    hit_rate: float
    turnover: float
    screen: PairScreenResult | None = None
    notes: list[str] = field(default_factory=list)


def pair_leg_weights(beta: float, mode: str = "cointegration", sigma_a: float = np.nan, sigma_b: float = np.nan) -> tuple[float, float]:
    """Gross-notional weights for long A / short ``β`` B.

    ``cointegration`` uses the statistical hedge ratio. ``vol_neutral``
    equalizes ``|w| σ`` on each leg and keeps the short on B.
    """

    if mode == "vol_neutral" and np.isfinite(sigma_a) and np.isfinite(sigma_b) and sigma_a > 0 and sigma_b > 0:
        raw_a = 1.0 / sigma_a
        raw_b = 1.0 / sigma_b
        gross = raw_a + raw_b
        return raw_a / gross, -raw_b / gross
    gross = 1.0 + abs(beta)
    if gross <= 0.0:
        return 0.0, 0.0
    return 1.0 / gross, -beta / gross


def market_residual_returns(returns: FloatArray, market: FloatArray) -> tuple[FloatArray, float]:
    """CAPM residual ``r - β r_m`` estimated on the supplied window."""

    asset = np.asarray(returns, dtype=np.float64)
    mkt = np.asarray(market, dtype=np.float64)
    mask = np.isfinite(asset) & np.isfinite(mkt)
    if int(np.count_nonzero(mask)) < 5 or float(np.var(mkt[mask])) <= 0.0:
        return asset.copy(), np.nan
    beta = float(np.cov(asset[mask], mkt[mask])[0, 1] / np.var(mkt[mask]))
    return asset - beta * mkt, beta


def volume_spread_z(volumes_a: FloatArray, volumes_b: FloatArray, window: int, gamma: float = 1.0) -> FloatArray:
    """``z(log V_A) - γ z(log V_B)``."""

    log_a = np.log(np.maximum(np.asarray(volumes_a, dtype=np.float64), 1e-12))
    log_b = np.log(np.maximum(np.asarray(volumes_b, dtype=np.float64), 1e-12))
    return rolling_zscore(log_a, window) - gamma * rolling_zscore(log_b, window)


def volatility_spread_z(prices_a: FloatArray, prices_b: FloatArray, window: int, delta: float = 1.0) -> FloatArray:
    """``z(σ_A) - δ z(σ_B)`` using trailing realized volatility."""

    vol_a = realized_volatility(prices_a, window)
    vol_b = realized_volatility(prices_b, window)
    return rolling_zscore(vol_a, window) - delta * rolling_zscore(vol_b, window)


def composite_signal(
    price_z: FloatArray,
    volume_z: FloatArray | None = None,
    vol_z: FloatArray | None = None,
    weights: tuple[float, float, float] = (1.0, 0.0, 0.0),
) -> FloatArray:
    """Weighted combination of price, volume, and volatility z-scores.

    Zero-weight or non-finite features are ignored so a missing volume
    observation cannot turn a valid price z-score into NaN.
    """

    signal = weights[0] * np.asarray(price_z, dtype=np.float64)
    extras = ((volume_z, weights[1]), (vol_z, weights[2]))
    for feature, weight in extras:
        if feature is None or weight == 0.0:
            continue
        values = np.asarray(feature, dtype=np.float64)
        signal = np.where(np.isfinite(values), signal + weight * values, signal)
    return signal


def detect_regime_break(
    adf_pvalue: float,
    half_life: float,
    reference_half_life: float,
    beta: float,
    reference_beta: float,
    zscore: float,
    stop_z: float,
    half_life_mult: float = 2.0,
    beta_change: float = 0.35,
) -> bool:
    """Return True when mean-reversion is no longer a reasonable hypothesis."""

    if np.isfinite(zscore) and abs(zscore) >= stop_z:
        return True
    if np.isfinite(adf_pvalue) and adf_pvalue > 0.10:
        return True
    if (
        np.isfinite(half_life)
        and np.isfinite(reference_half_life)
        and reference_half_life > 0
        and half_life > half_life_mult * reference_half_life
    ):
        return True
    if np.isfinite(beta) and np.isfinite(reference_beta) and abs(reference_beta) > 1e-8:
        if abs(beta - reference_beta) / abs(reference_beta) > beta_change:
            return True
    return False


def screen_pair(
    prices_a: FloatArray,
    prices_b: FloatArray,
    fundamentals_a: FundamentalSnapshot | None = None,
    fundamentals_b: FundamentalSnapshot | None = None,
    volumes_a: FloatArray | None = None,
    volumes_b: FloatArray | None = None,
    config: PairStrategyConfig | None = None,
    fair_coef: FairRatioCoef | None = None,
) -> PairScreenResult:
    """Run the fundamental + cointegration + mean-reversion quality screen."""

    cfg = PairStrategyConfig() if config is None else config
    reasons: list[str] = []
    prices_a = np.asarray(prices_a, dtype=np.float64)
    prices_b = np.asarray(prices_b, dtype=np.float64)
    if prices_a.size != prices_b.size:
        raise ValueError("price series must have the same length")
    if prices_a.size < 40:
        raise ValueError("need at least 40 observations to screen a pair")

    distance = np.nan
    mispricing = np.nan
    if fundamentals_a is not None and fundamentals_b is not None:
        if cfg.require_same_industry and not same_industry(fundamentals_a, fundamentals_b):
            reasons.append("industry mismatch")
        distance = fundamental_distance(fundamentals_a, fundamentals_b)
        if np.isfinite(distance) and distance >= cfg.max_fundamental_distance:
            reasons.append(f"fundamental distance {distance:.3f} >= {cfg.max_fundamental_distance}")
        mispricing = relative_value_mispricing(
            float(prices_a[-1]),
            float(prices_b[-1]),
            fundamentals_a,
            fundamentals_b,
            coef=fair_coef,
        )
        for snapshot in (fundamentals_a, fundamentals_b):
            if np.isfinite(snapshot.adv) and snapshot.adv < cfg.min_adv:
                reasons.append(f"{snapshot.ticker} ADV {snapshot.adv:.0f} below {cfg.min_adv:.0f}")
            if np.isfinite(snapshot.bid_ask_bps) and snapshot.bid_ask_bps > cfg.max_bid_ask_bps:
                reasons.append(f"{snapshot.ticker} bid-ask {snapshot.bid_ask_bps:.1f}bps too wide")

    if volumes_a is not None and volumes_b is not None:
        dollar_a = float(np.median(prices_a * np.asarray(volumes_a, dtype=np.float64)))
        dollar_b = float(np.median(prices_b * np.asarray(volumes_b, dtype=np.float64)))
        if dollar_a < cfg.min_adv:
            reasons.append("leg A dollar volume too low")
        if dollar_b < cfg.min_adv:
            reasons.append("leg B dollar volume too low")

    corr = return_correlation(prices_a, prices_b)
    if not np.isfinite(corr) or corr < cfg.min_correlation:
        reasons.append(f"return correlation {corr:.3f} < {cfg.min_correlation}")

    eg = engle_granger(prices_a, prices_b)
    if not eg.cointegrated or eg.adf.pvalue > cfg.max_adf_pvalue:
        reasons.append(f"not cointegrated (EG p={eg.adf.pvalue:.3f})")

    johansen = johansen_trace(prices_a, prices_b)
    ou = fit_ou(eg.hedge.residual)
    hurst = hurst_exponent(eg.hedge.residual)
    vr = variance_ratio(np.diff(eg.hedge.residual), period=5)

    if not np.isfinite(ou.half_life) or ou.half_life > cfg.max_half_life:
        reasons.append(f"half-life {ou.half_life:.1f} > {cfg.max_half_life:.0f}")
    if not np.isfinite(hurst) or hurst >= cfg.max_hurst:
        reasons.append(f"Hurst {hurst:.3f} >= {cfg.max_hurst}")
    if np.isfinite(vr) and vr >= 1.0:
        reasons.append(f"variance ratio {vr:.3f} does not indicate mean reversion")

    return PairScreenResult(
        passed=not reasons,
        reasons=tuple(reasons),
        correlation=float(corr),
        hedge_alpha=eg.hedge.alpha,
        hedge_beta=eg.hedge.beta,
        adf_pvalue=eg.adf.pvalue,
        johansen_cointegrated=johansen.cointegrated,
        half_life=ou.half_life,
        hurst=float(hurst),
        variance_ratio=float(vr),
        fundamental_distance=float(distance),
        mispricing=float(mispricing),
        ou=ou,
    )


def _live_window_ok(
    prices_a: FloatArray,
    prices_b: FloatArray,
    config: PairStrategyConfig,
) -> tuple[bool, str]:
    """Softer live checks used after a pair has already been selected."""

    corr = return_correlation(prices_a, prices_b)
    if not np.isfinite(corr) or corr < min(0.4, config.min_correlation * 0.7):
        return False, f"correlation collapsed to {corr:.3f}"
    hedge = estimate_hedge_ratio(prices_a, prices_b)
    ou = fit_ou(hedge.residual)
    if not np.isfinite(ou.half_life) or ou.half_life > max(90.0, config.max_half_life * 1.5):
        return False, f"half-life exploded to {ou.half_life:.1f}"
    hurst = hurst_exponent(hedge.residual)
    if np.isfinite(hurst) and hurst >= 0.6:
        return False, f"Hurst regime shift {hurst:.3f}"
    return True, ""


def _position_from_signal(
    signal: FloatArray,
    regime_break: FloatArray,
    config: PairStrategyConfig,
) -> FloatArray:
    """Classic hysteresis: enter at ``entry_z``, exit at ``exit_z`` / stop / time."""

    nobs = signal.shape[0]
    position = np.zeros(nobs, dtype=np.float64)
    state = 0.0
    holding = 0
    for t in range(nobs):
        if regime_break[t]:
            state = 0.0
            holding = 0
            position[t] = 0.0
            continue
        z_t = signal[t]
        if not np.isfinite(z_t):
            position[t] = state
            if state != 0.0:
                holding += 1
            continue
        if state == 0.0:
            if z_t > config.entry_z:
                state = -1.0
                holding = 1
            elif z_t < -config.entry_z:
                state = 1.0
                holding = 1
        else:
            holding += 1
            if abs(z_t) <= config.exit_z or abs(z_t) >= config.stop_z or holding > config.max_holding_days:
                state = 0.0
                holding = 0
        position[t] = state
    return position


def _count_trades(position: FloatArray) -> int:
    """Count entries, including the initial position if it starts in the market."""

    lagged = np.concatenate([[0.0], position[:-1]])
    entries = (lagged == 0.0) & (position != 0.0)
    return int(np.count_nonzero(entries))


def _trade_hit_rate(position: FloatArray, pnl: FloatArray) -> float:
    """Share of round-trips with positive completed-trade PnL."""

    wins = 0
    trades = 0
    running = 0.0
    in_trade = False
    lagged = np.concatenate([[0.0], position[:-1]])
    for t, (prev, curr) in enumerate(zip(lagged, position)):
        if prev == 0.0 and curr != 0.0:
            in_trade = True
            running = 0.0
        if in_trade:
            running += float(pnl[t])
        if in_trade and prev != 0.0 and curr == 0.0:
            trades += 1
            wins += int(running > 0.0)
            in_trade = False
            running = 0.0
    if trades == 0:
        return np.nan
    return wins / trades


def _annualized_sharpe(pnl: FloatArray) -> float:
    """Annualize daily PnL with 252 trading days, ignoring NaNs."""

    values = np.asarray(pnl, dtype=np.float64)
    values = values[np.isfinite(values)]
    if values.size < 2:
        return np.nan
    scale = float(np.std(values, ddof=1))
    if scale <= 0.0:
        return np.nan
    return float(np.mean(values) / scale * np.sqrt(252.0))


def run_pair_backtest(
    prices_a: FloatArray,
    prices_b: FloatArray,
    volumes_a: FloatArray | None = None,
    volumes_b: FloatArray | None = None,
    fundamentals_a: FundamentalSnapshot | None = None,
    fundamentals_b: FundamentalSnapshot | None = None,
    market_returns: FloatArray | None = None,
    config: PairStrategyConfig | None = None,
) -> BacktestResult:
    """Walk-forward pairs backtest with next-bar execution and cost drag.

    Hedge ratios are estimated only on the formation window. Signals at
    close ``t`` are executed at the return from ``t`` to ``t+1``, which
    removes look-ahead from fills. Positions flatten at each window
    boundary so a newly estimated β cannot rewrite an open trade's PnL.
    """

    cfg = PairStrategyConfig() if config is None else config
    prices_a = np.asarray(prices_a, dtype=np.float64)
    prices_b = np.asarray(prices_b, dtype=np.float64)
    nobs = prices_a.size
    if nobs != prices_b.size:
        raise ValueError("price series must have the same length")
    if nobs <= cfg.formation_window + 5:
        raise ValueError("series is shorter than formation_window plus a trading buffer")

    ret_a = np.zeros(nobs, dtype=np.float64)
    ret_b = np.zeros(nobs, dtype=np.float64)
    ret_a[1:] = simple_returns(prices_a)
    ret_b[1:] = simple_returns(prices_b)
    if market_returns is not None:
        residual_a, _ = market_residual_returns(ret_a, np.asarray(market_returns, dtype=np.float64))
        residual_b, _ = market_residual_returns(ret_b, np.asarray(market_returns, dtype=np.float64))
        ret_a, ret_b = residual_a, residual_b

    spread = np.full(nobs, np.nan, dtype=np.float64)
    zscore = np.full(nobs, np.nan, dtype=np.float64)
    signal = np.full(nobs, np.nan, dtype=np.float64)
    beta_path = np.full(nobs, np.nan, dtype=np.float64)
    regime = np.zeros(nobs, dtype=np.float64)
    intended = np.zeros(nobs, dtype=np.float64)
    notes: list[str] = []
    initial_screen: PairScreenResult | None = None

    start = cfg.formation_window
    while start < nobs - 2:
        stop = min(start + cfg.trade_window, nobs)
        train_a = prices_a[start - cfg.formation_window : start]
        train_b = prices_b[start - cfg.formation_window : start]
        train_vol_a = None if volumes_a is None else np.asarray(volumes_a, dtype=np.float64)[start - cfg.formation_window : start]
        train_vol_b = None if volumes_b is None else np.asarray(volumes_b, dtype=np.float64)[start - cfg.formation_window : start]
        if initial_screen is None or cfg.strict_walkforward_screen:
            screen = screen_pair(
                train_a,
                train_b,
                fundamentals_a=fundamentals_a,
                fundamentals_b=fundamentals_b,
                volumes_a=train_vol_a,
                volumes_b=train_vol_b,
                config=cfg,
            )
            if initial_screen is None:
                initial_screen = screen
        if cfg.strict_walkforward_screen:
            tradable = screen.passed
            skip_reason = "; ".join(screen.reasons)
        else:
            tradable, skip_reason = _live_window_ok(train_a, train_b, cfg)
        if not tradable:
            notes.append(f"skip {start}:{stop} ({skip_reason})")
            start = stop
            continue

        hedge = estimate_hedge_ratio(train_a, train_b)
        beta_path[start:stop] = hedge.beta
        window_spread = construct_spread(prices_a[:stop], prices_b[:stop], hedge.alpha, hedge.beta)
        spread[start:stop] = window_spread[start:stop]
        window_z = rolling_zscore(window_spread, cfg.z_window)
        zscore[start:stop] = window_z[start:stop]

        vol_z = None
        volume_z = None
        if volumes_a is not None and volumes_b is not None:
            volume_z = volume_spread_z(
                np.asarray(volumes_a, dtype=np.float64)[:stop],
                np.asarray(volumes_b, dtype=np.float64)[:stop],
                cfg.z_window,
            )
        vol_z = volatility_spread_z(prices_a[:stop], prices_b[:stop], cfg.vol_window)
        combined = composite_signal(
            window_z,
            volume_z=None if volume_z is None else volume_z,
            vol_z=vol_z,
            weights=cfg.signal_weights,
        )
        signal[start:stop] = combined[start:stop]

        live_break = np.zeros(stop, dtype=np.float64)
        ref_ou = fit_ou(hedge.residual)
        ref_half = ref_ou.half_life
        ref_beta = hedge.beta
        for t in range(start, stop):
            lookback_start = max(0, t - cfg.formation_window + 1)
            local_spread = window_spread[lookback_start : t + 1]
            local_break = False
            if local_spread.size >= 40 and np.all(np.isfinite(local_spread)):
                local_ou = fit_ou(local_spread)
                local_beta = hedge.beta
                if t - start >= 20:
                    est_start = max(0, t - cfg.formation_window + 1)
                    if t - est_start + 1 >= 60:
                        local_beta = estimate_hedge_ratio(
                            prices_a[est_start : t + 1],
                            prices_b[est_start : t + 1],
                        ).beta
                local_break = detect_regime_break(
                    adf_pvalue=np.nan,
                    half_life=local_ou.half_life,
                    reference_half_life=ref_half,
                    beta=local_beta,
                    reference_beta=ref_beta,
                    zscore=float(window_z[t]),
                    stop_z=cfg.stop_z,
                )
            if local_break:
                live_break[t] = 1.0
                regime[t] = 1.0
        intended[start:stop] = _position_from_signal(combined[start:stop], live_break[start:stop], cfg)
        start = stop

    executed = np.zeros(nobs, dtype=np.float64)
    executed[1:] = intended[:-1]

    weights_a = np.zeros(nobs, dtype=np.float64)
    weights_b = np.zeros(nobs, dtype=np.float64)
    sigma_a = rolling_std(ret_a, cfg.vol_window)
    sigma_b = rolling_std(ret_b, cfg.vol_window)
    spread_ret = np.zeros(nobs, dtype=np.float64)
    for t in range(nobs):
        beta_t = beta_path[t]
        if not np.isfinite(beta_t):
            beta_t = 1.0
        w_a, w_b = pair_leg_weights(beta_t, mode="cointegration")
        scale = 1.0
        if t > 0 and np.isfinite(sigma_a[t]) and np.isfinite(sigma_b[t]):
            port_vol = abs(w_a) * sigma_a[t] + abs(w_b) * sigma_b[t]
            if port_vol > 0.0:
                scale = min(cfg.max_leverage, cfg.target_daily_vol / port_vol)
        weights_a[t] = executed[t] * w_a * scale
        weights_b[t] = executed[t] * w_b * scale
        spread_ret[t] = weights_a[t] * ret_a[t] + weights_b[t] * ret_b[t]

    turnover = np.zeros(nobs, dtype=np.float64)
    turnover[1:] = np.abs(np.diff(weights_a)) + np.abs(np.diff(weights_b))
    costs = turnover * (cfg.cost_bps / 10000.0)
    pnl = spread_ret - costs
    equity = np.cumsum(pnl)
    n_trades = _count_trades(executed)
    return BacktestResult(
        positions=executed,
        weights_a=weights_a,
        weights_b=weights_b,
        spread=spread,
        zscore=zscore,
        pnl=pnl,
        equity=equity,
        beta_path=beta_path,
        regime_break=regime,
        n_trades=n_trades,
        sharpe=_annualized_sharpe(pnl),
        total_return=float(equity[-1]) if equity.size else 0.0,
        hit_rate=_trade_hit_rate(executed, pnl),
        turnover=float(np.sum(turnover)),
        screen=initial_screen,
        notes=notes,
    )


def load_pair_csv(
    path: str,
    column_a: str = "close_a",
    column_b: str = "close_b",
    volume_a: str | None = "volume_a",
    volume_b: str | None = "volume_b",
) -> dict[str, FloatArray]:
    """Load a pair CSV with named columns into numpy arrays.

    The file must have a header. Extra columns are ignored. Missing volume
    columns are omitted from the result rather than filled.
    """

    import csv
    from pathlib import Path

    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header")
        rows = list(reader)
    if not rows:
        raise ValueError(f"{path} is empty")

    def _column(name: str) -> FloatArray:
        if name not in rows[0]:
            raise KeyError(f"column {name!r} not in {path}")
        return np.asarray([float(row[name]) for row in rows], dtype=np.float64)

    data = {"prices_a": _column(column_a), "prices_b": _column(column_b)}
    if volume_a and volume_a in rows[0]:
        data["volumes_a"] = _column(volume_a)
    if volume_b and volume_b in rows[0]:
        data["volumes_b"] = _column(volume_b)
    return data
