#!/usr/bin/env python3
"""Download US-listed daily OHLCV data from 2010 onward.

The default symbol universe comes from Nasdaq Trader's current US listings.
Historical delisted symbols are not included by that free source.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import dataclasses
import datetime as dt
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Iterable, Sequence


NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
USER_AGENT = "Mozilla/5.0 (compatible; us-daily-data-downloader/1.0)"


@dataclasses.dataclass(frozen=True)
class ListedSymbol:
    ticker: str
    name: str
    exchange: str
    is_etf: bool
    source: str


@dataclasses.dataclass(frozen=True)
class DownloadResult:
    ticker: str
    yahoo_symbol: str
    status: str
    rows: int
    path: str
    message: str = ""


def parse_date(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Expected YYYY-MM-DD, got {value!r}") from exc


def request_text(url: str, *, timeout: int, retries: int, backoff: float) -> str:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt == retries:
                break
            time.sleep(backoff * (2**attempt))
    raise RuntimeError(f"Failed to fetch {url}: {last_error}") from last_error


def _pipe_rows(text: str) -> list[str]:
    return [line for line in text.splitlines() if "|" in line and not line.startswith("File Creation Time")]


def _is_yes(value: str | None) -> bool:
    return (value or "").strip().upper() == "Y"


def parse_nasdaq_listed(text: str, *, include_etfs: bool, include_non_stocks: bool = False) -> list[ListedSymbol]:
    rows = csv.DictReader(_pipe_rows(text), delimiter="|")
    symbols: list[ListedSymbol] = []
    for row in rows:
        ticker = (row.get("Symbol") or "").strip()
        name = (row.get("Security Name") or "").strip()
        if not ticker or _is_yes(row.get("Test Issue")):
            continue
        is_etf = _is_yes(row.get("ETF"))
        if is_etf and not include_etfs:
            continue
        if not include_non_stocks and not is_stock_like_security(name):
            continue
        symbols.append(
            ListedSymbol(
                ticker=ticker,
                name=name,
                exchange="NASDAQ",
                is_etf=is_etf,
                source="nasdaqlisted",
            )
        )
    return symbols


def parse_other_listed(text: str, *, include_etfs: bool, include_non_stocks: bool = False) -> list[ListedSymbol]:
    exchange_names = {
        "A": "NYSE American",
        "N": "NYSE",
        "P": "NYSE Arca",
        "Z": "Cboe BZX",
        "V": "IEX",
    }
    rows = csv.DictReader(_pipe_rows(text), delimiter="|")
    symbols: list[ListedSymbol] = []
    for row in rows:
        ticker = (row.get("ACT Symbol") or "").strip()
        name = (row.get("Security Name") or "").strip()
        if not ticker or _is_yes(row.get("Test Issue")):
            continue
        is_etf = _is_yes(row.get("ETF"))
        if is_etf and not include_etfs:
            continue
        if not include_non_stocks and not is_stock_like_security(name):
            continue
        exchange_code = (row.get("Exchange") or "").strip()
        symbols.append(
            ListedSymbol(
                ticker=ticker,
                name=name,
                exchange=exchange_names.get(exchange_code, exchange_code or "OTHER"),
                is_etf=is_etf,
                source="otherlisted",
            )
        )
    return symbols


def is_stock_like_security(name: str) -> bool:
    """Filter out exchange-listed instruments that are not operating-company stock."""
    lower_name = name.lower()
    hard_exclusions = [
        r"\bunits?\b",
        r"\bwarrants?\b",
        r"\brights?\b",
        r"\bnotes?\b",
        r"\bbonds?\b",
        r"\bdebentures?\b",
        r"\bpreferred\b",
        r"\bpreference\b",
    ]
    return not any(re.search(pattern, lower_name) for pattern in hard_exclusions)


def to_yahoo_symbol(ticker: str) -> str:
    return ticker.strip().replace(".", "-").replace("/", "-")


def safe_filename(symbol: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", symbol)


def load_symbols(
    *,
    explicit_symbols: Sequence[str],
    symbols_file: pathlib.Path | None,
    include_etfs: bool,
    include_non_stocks: bool,
    timeout: int,
    retries: int,
    backoff: float,
) -> list[ListedSymbol]:
    if explicit_symbols:
        return [
            ListedSymbol(ticker=s.strip().upper(), name="", exchange="manual", is_etf=False, source="manual")
            for s in explicit_symbols
            if s.strip()
        ]
    if symbols_file:
        return [
            ListedSymbol(ticker=line.strip().upper(), name="", exchange="file", is_etf=False, source="file")
            for line in symbols_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]

    nasdaq_text = request_text(NASDAQ_LISTED_URL, timeout=timeout, retries=retries, backoff=backoff)
    other_text = request_text(OTHER_LISTED_URL, timeout=timeout, retries=retries, backoff=backoff)
    symbols = parse_nasdaq_listed(nasdaq_text, include_etfs=include_etfs, include_non_stocks=include_non_stocks)
    symbols.extend(parse_other_listed(other_text, include_etfs=include_etfs, include_non_stocks=include_non_stocks))
    return dedupe_symbols(symbols)


def dedupe_symbols(symbols: Iterable[ListedSymbol]) -> list[ListedSymbol]:
    seen: set[str] = set()
    unique: list[ListedSymbol] = []
    for symbol in symbols:
        key = symbol.ticker.upper()
        if key in seen:
            continue
        seen.add(key)
        unique.append(symbol)
    return unique


def yahoo_chart_url(symbol: str, start: dt.date, end: dt.date) -> str:
    period1 = int(dt.datetime.combine(start, dt.time.min, tzinfo=dt.timezone.utc).timestamp())
    exclusive_end = end + dt.timedelta(days=1)
    period2 = int(dt.datetime.combine(exclusive_end, dt.time.min, tzinfo=dt.timezone.utc).timestamp())
    params = urllib.parse.urlencode(
        {
            "period1": period1,
            "period2": period2,
            "interval": "1d",
            "events": "history",
            "includeAdjustedClose": "true",
        }
    )
    return f"{YAHOO_CHART_URL.format(symbol=urllib.parse.quote(symbol))}?{params}"


def parse_yahoo_chart(payload: str) -> list[dict[str, object]]:
    data = json.loads(payload)
    chart = data.get("chart") or {}
    error = chart.get("error")
    if error:
        description = error.get("description") if isinstance(error, dict) else error
        raise RuntimeError(str(description))

    results = chart.get("result") or []
    if not results:
        return []

    result = results[0]
    timestamps = result.get("timestamp") or []
    indicators = result.get("indicators") or {}
    quotes = indicators.get("quote") or [{}]
    quote = quotes[0]
    adjcloses = indicators.get("adjclose") or [{}]
    adjclose = adjcloses[0].get("adjclose") if adjcloses else []

    rows: list[dict[str, object]] = []
    for index, timestamp in enumerate(timestamps):
        row = {
            "Date": dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc).date().isoformat(),
            "Open": _value_at(quote.get("open"), index),
            "High": _value_at(quote.get("high"), index),
            "Low": _value_at(quote.get("low"), index),
            "Close": _value_at(quote.get("close"), index),
            "Adj Close": _value_at(adjclose, index),
            "Volume": _value_at(quote.get("volume"), index),
        }
        if row["Open"] is None or row["Close"] is None:
            continue
        rows.append(row)
    return rows


def _value_at(values: object, index: int) -> object:
    if not isinstance(values, list) or index >= len(values):
        return None
    return values[index]


def write_price_csv(path: pathlib.Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"])
        writer.writeheader()
        writer.writerows(rows)


def download_symbol(
    symbol: ListedSymbol,
    *,
    start: dt.date,
    end: dt.date,
    output_dir: pathlib.Path,
    force: bool,
    timeout: int,
    retries: int,
    backoff: float,
) -> DownloadResult:
    yahoo_symbol = to_yahoo_symbol(symbol.ticker)
    output_path = output_dir / f"{safe_filename(yahoo_symbol)}.csv"
    if output_path.exists() and not force:
        return DownloadResult(symbol.ticker, yahoo_symbol, "skipped", 0, str(output_path), "file exists")

    try:
        payload = request_text(yahoo_chart_url(yahoo_symbol, start, end), timeout=timeout, retries=retries, backoff=backoff)
        rows = parse_yahoo_chart(payload)
        if not rows:
            return DownloadResult(symbol.ticker, yahoo_symbol, "empty", 0, str(output_path), "no rows returned")
        write_price_csv(output_path, rows)
        return DownloadResult(symbol.ticker, yahoo_symbol, "ok", len(rows), str(output_path))
    except Exception as exc:  # noqa: BLE001 - capture per-symbol errors so long runs can continue.
        return DownloadResult(symbol.ticker, yahoo_symbol, "error", 0, str(output_path), str(exc))


def write_manifest(path: pathlib.Path, results: Sequence[DownloadResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["ticker", "yahoo_symbol", "status", "rows", "path", "message"])
        writer.writeheader()
        for result in results:
            writer.writerow(dataclasses.asdict(result))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download US-listed daily stock data as one CSV per symbol.")
    parser.add_argument("--start", type=parse_date, default=dt.date(2010, 1, 1), help="Start date, default: 2010-01-01")
    parser.add_argument("--end", type=parse_date, default=dt.date.today(), help="End date, default: today")
    parser.add_argument("--output", type=pathlib.Path, default=pathlib.Path("data/us_daily"), help="Output directory")
    parser.add_argument(
        "--manifest",
        type=pathlib.Path,
        default=pathlib.Path("data/us_daily_manifest.csv"),
        help="Manifest CSV path",
    )
    parser.add_argument("--symbols", default="", help="Comma-separated tickers, useful for smoke tests")
    parser.add_argument("--symbols-file", type=pathlib.Path, help="Newline-separated tickers")
    parser.add_argument("--include-etfs", action="store_true", help="Include ETFs in addition to common stocks")
    parser.add_argument("--include-non-stocks", action="store_true", help="Include warrants, units, rights, notes, and preferreds")
    parser.add_argument("--limit", type=int, help="Limit number of symbols, useful for smoke tests")
    parser.add_argument("--workers", type=int, default=4, help="Concurrent downloads, default: 4")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout seconds, default: 30")
    parser.add_argument("--retries", type=int, default=2, help="Retries per request, default: 2")
    parser.add_argument("--backoff", type=float, default=1.0, help="Retry backoff seconds, default: 1.0")
    parser.add_argument("--force", action="store_true", help="Overwrite existing symbol CSV files")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.end < args.start:
        raise SystemExit("--end must be on or after --start")
    if args.workers < 1:
        raise SystemExit("--workers must be at least 1")

    explicit_symbols = [symbol for symbol in args.symbols.split(",") if symbol.strip()]
    symbols = load_symbols(
        explicit_symbols=explicit_symbols,
        symbols_file=args.symbols_file,
        include_etfs=args.include_etfs,
        include_non_stocks=args.include_non_stocks,
        timeout=args.timeout,
        retries=args.retries,
        backoff=args.backoff,
    )
    if args.limit:
        symbols = symbols[: args.limit]

    print(f"Downloading {len(symbols)} symbols from {args.start} to {args.end} into {args.output}")
    results: list[DownloadResult] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_symbol = {
            executor.submit(
                download_symbol,
                symbol,
                start=args.start,
                end=args.end,
                output_dir=args.output,
                force=args.force,
                timeout=args.timeout,
                retries=args.retries,
                backoff=args.backoff,
            ): symbol
            for symbol in symbols
        }
        for index, future in enumerate(concurrent.futures.as_completed(future_to_symbol), start=1):
            result = future.result()
            results.append(result)
            print(f"[{index}/{len(symbols)}] {result.ticker}: {result.status} ({result.rows} rows) {result.message}")

    results.sort(key=lambda item: item.ticker)
    write_manifest(args.manifest, results)
    ok_count = sum(1 for result in results if result.status in {"ok", "skipped"})
    error_count = len(results) - ok_count
    print(f"Done. ok_or_skipped={ok_count} errors_or_empty={error_count} manifest={args.manifest}")
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
