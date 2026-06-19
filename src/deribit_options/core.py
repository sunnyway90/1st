"""Utilities for Deribit BTC option snapshots and ATM daily changes.

Deribit's public API exposes current option-chain metadata and book summaries.
This module keeps historical ATM analysis explicit: collect snapshots regularly
with :func:`fetch_btc_option_snapshot`, persist them to CSV, then compute daily
ATM changes from those stored observations.
"""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from statistics import median
from typing import Any, Iterable
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DERIBIT_PRODUCTION_URL = "https://www.deribit.com/api/v2"
OPTION_NAME_RE = re.compile(
    r"^(?P<base>[A-Z]+)(?:_[A-Z]+)?-"
    r"(?P<expiry>\d{1,2}[A-Z]{3}\d{2})-"
    r"(?P<strike>\d+(?:\.\d+)?)-"
    r"(?P<option>[CP])$"
)
CSV_FIELDS = [
    "snapshot_time",
    "instrument_name",
    "expiration",
    "strike",
    "option_type",
    "underlying_price",
    "mark_iv",
    "mark_price",
    "bid_price",
    "ask_price",
    "mid_price",
    "open_interest",
    "volume",
]


class DeribitAPIError(RuntimeError):
    """Raised when Deribit returns an API error or malformed response."""


@dataclass(frozen=True)
class ParsedOptionName:
    """Parts encoded in a Deribit option instrument name."""

    base_currency: str
    expiration: date
    strike: float
    option_type: str


@dataclass(frozen=True)
class DeribitOptionQuote:
    """One option quote observation from a Deribit chain snapshot."""

    snapshot_time: datetime
    instrument_name: str
    expiration: date
    strike: float
    option_type: str
    underlying_price: float | None = None
    mark_iv: float | None = None
    mark_price: float | None = None
    bid_price: float | None = None
    ask_price: float | None = None
    mid_price: float | None = None
    open_interest: float | None = None
    volume: float | None = None


@dataclass(frozen=True)
class AtmOptionPoint:
    """ATM call/put pair selected for one snapshot date."""

    snapshot_date: date
    expiration: date
    underlying_price: float
    strike: float
    strike_distance_pct: float
    call_instrument_name: str | None
    put_instrument_name: str | None
    call_mark_iv: float | None
    put_mark_iv: float | None
    average_mark_iv: float | None
    call_mark_price: float | None
    put_mark_price: float | None
    straddle_mark_price: float | None
    open_interest: float | None
    volume: float | None


@dataclass(frozen=True)
class AtmOptionDailyChange:
    """ATM point plus day-over-day changes versus the previous point."""

    point: AtmOptionPoint
    underlying_change: float | None
    strike_change: float | None
    average_mark_iv_change: float | None
    straddle_mark_price_change: float | None


class DeribitPublicClient:
    """Small HTTP JSON-RPC client for Deribit's unauthenticated market data API."""

    def __init__(self, base_url: str = DERIBIT_PRODUCTION_URL, *, timeout: float = 20.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        """Call a public Deribit method and return the ``result`` payload."""

        if not method.startswith("public/"):
            raise ValueError("only public Deribit methods are supported")

        query = urlencode(params or {})
        url = f"{self.base_url}/{method}"
        if query:
            url = f"{url}?{query}"
        request = Request(url, headers={"User-Agent": "deribit-options-module/0.1"})
        with urlopen(request, timeout=self.timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if "error" in payload:
            raise DeribitAPIError(str(payload["error"]))
        if "result" not in payload:
            raise DeribitAPIError(f"missing result in Deribit response for {method}")
        return payload["result"]

    def get_instruments(
        self,
        *,
        currency: str = "BTC",
        kind: str = "option",
        expired: bool = False,
    ) -> list[dict[str, Any]]:
        """Return Deribit instruments, usually BTC options."""

        return list(
            self.request(
                "public/get_instruments",
                {"currency": currency, "kind": kind, "expired": str(expired).lower()},
            )
        )

    def get_book_summary_by_currency(
        self,
        *,
        currency: str = "BTC",
        kind: str = "option",
    ) -> list[dict[str, Any]]:
        """Return current book summaries for a currency and instrument kind."""

        return list(self.request("public/get_book_summary_by_currency", {"currency": currency, "kind": kind}))

    def get_historical_volatility(self, *, currency: str = "BTC") -> list[list[float]]:
        """Return Deribit's historical underlying volatility series.

        This is not an option-chain history endpoint, but it is useful context
        when comparing ATM implied volatility with realized volatility.
        """

        return list(self.request("public/get_historical_volatility", {"currency": currency}))


def parse_option_instrument_name(instrument_name: str) -> ParsedOptionName:
    """Parse Deribit option names such as ``BTC-9DEC24-102000-C``."""

    match = OPTION_NAME_RE.match(instrument_name)
    if match is None:
        raise ValueError(f"not a Deribit option instrument name: {instrument_name}")

    expiration = datetime.strptime(match.group("expiry"), "%d%b%y").date()
    return ParsedOptionName(
        base_currency=match.group("base"),
        expiration=expiration,
        strike=float(match.group("strike")),
        option_type="call" if match.group("option") == "C" else "put",
    )


def fetch_btc_option_snapshot(
    client: DeribitPublicClient | None = None,
    *,
    as_of: datetime | None = None,
) -> list[DeribitOptionQuote]:
    """Fetch the current BTC option chain snapshot from Deribit."""

    deribit = client or DeribitPublicClient()
    instruments = deribit.get_instruments(currency="BTC", kind="option")
    summaries = deribit.get_book_summary_by_currency(currency="BTC", kind="option")
    return build_option_quotes(instruments, summaries, as_of=as_of)


def build_option_quotes(
    instruments: Iterable[dict[str, Any]],
    summaries: Iterable[dict[str, Any]],
    *,
    as_of: datetime | None = None,
) -> list[DeribitOptionQuote]:
    """Merge instrument metadata with current book summaries."""

    snapshot_time = _ensure_utc(as_of or datetime.now(timezone.utc))
    instruments_by_name = {str(item["instrument_name"]): item for item in instruments if "instrument_name" in item}
    quotes: list[DeribitOptionQuote] = []

    for summary in summaries:
        instrument_name = str(summary.get("instrument_name", ""))
        if not instrument_name:
            continue
        instrument = instruments_by_name.get(instrument_name, {})
        parsed = parse_option_instrument_name(instrument_name)
        expiration = _date_from_timestamp(instrument.get("expiration_timestamp")) or parsed.expiration
        strike = _optional_float(instrument.get("strike"))
        option_type = instrument.get("option_type") or parsed.option_type

        quotes.append(
            DeribitOptionQuote(
                snapshot_time=snapshot_time,
                instrument_name=instrument_name,
                expiration=expiration,
                strike=float(strike if strike is not None else parsed.strike),
                option_type=str(option_type),
                underlying_price=_optional_float(summary.get("underlying_price")),
                mark_iv=_optional_float(summary.get("mark_iv")),
                mark_price=_optional_float(summary.get("mark_price")),
                bid_price=_optional_float(summary.get("bid_price")),
                ask_price=_optional_float(summary.get("ask_price")),
                mid_price=_optional_float(summary.get("mid_price")),
                open_interest=_optional_float(summary.get("open_interest")),
                volume=_optional_float(summary.get("volume")),
            )
        )

    return quotes


def select_atm_option_pair(
    quotes: Iterable[DeribitOptionQuote],
    *,
    as_of_date: date | None = None,
    target_expiration: date | None = None,
    target_days_to_expiration: int | None = None,
    min_days_to_expiration: int = 1,
) -> AtmOptionPoint | None:
    """Select the ATM call/put pair from one snapshot's option quotes.

    If no target expiration is provided, the front non-expired expiry is used.
    A ``target_days_to_expiration`` can be supplied to track a steadier tenor.
    """

    quote_list = [quote for quote in quotes if quote.underlying_price is not None]
    if not quote_list:
        return None

    snapshot_date = as_of_date or max(quote.snapshot_time for quote in quote_list).date()
    expiration = _choose_expiration(
        quote_list,
        snapshot_date=snapshot_date,
        target_expiration=target_expiration,
        target_days_to_expiration=target_days_to_expiration,
        min_days_to_expiration=min_days_to_expiration,
    )
    if expiration is None:
        return None

    expiry_quotes = [quote for quote in quote_list if quote.expiration == expiration]
    underlying_price = float(median(float(quote.underlying_price) for quote in expiry_quotes if quote.underlying_price))
    by_strike: dict[float, list[DeribitOptionQuote]] = defaultdict(list)
    for quote in expiry_quotes:
        by_strike[quote.strike].append(quote)

    def strike_score(item: tuple[float, list[DeribitOptionQuote]]) -> tuple[int, float]:
        strike, strike_quotes = item
        option_types = {quote.option_type for quote in strike_quotes}
        missing_pair = 0 if {"call", "put"}.issubset(option_types) else 1
        return missing_pair, abs(strike - underlying_price)

    strike, strike_quotes = min(by_strike.items(), key=strike_score)
    call = _first_option(strike_quotes, "call")
    put = _first_option(strike_quotes, "put")
    average_mark_iv = _average_present([_field(call, "mark_iv"), _field(put, "mark_iv")])
    straddle_mark_price = _sum_present([_field(call, "mark_price"), _field(put, "mark_price")])
    open_interest = _sum_present([_field(call, "open_interest"), _field(put, "open_interest")])
    volume = _sum_present([_field(call, "volume"), _field(put, "volume")])

    return AtmOptionPoint(
        snapshot_date=snapshot_date,
        expiration=expiration,
        underlying_price=underlying_price,
        strike=float(strike),
        strike_distance_pct=abs(float(strike) - underlying_price) / underlying_price,
        call_instrument_name=call.instrument_name if call else None,
        put_instrument_name=put.instrument_name if put else None,
        call_mark_iv=call.mark_iv if call else None,
        put_mark_iv=put.mark_iv if put else None,
        average_mark_iv=average_mark_iv,
        call_mark_price=call.mark_price if call else None,
        put_mark_price=put.mark_price if put else None,
        straddle_mark_price=straddle_mark_price,
        open_interest=open_interest,
        volume=volume,
    )


def atm_daily_changes(
    quotes: Iterable[DeribitOptionQuote],
    *,
    target_expiration: date | None = None,
    target_days_to_expiration: int | None = None,
    min_days_to_expiration: int = 1,
) -> list[AtmOptionDailyChange]:
    """Calculate BTC ATM option daily changes from stored quote snapshots."""

    snapshots_by_day_time: dict[tuple[date, datetime], list[DeribitOptionQuote]] = defaultdict(list)
    for quote in quotes:
        snapshots_by_day_time[(quote.snapshot_time.date(), quote.snapshot_time)].append(quote)

    latest_time_by_day: dict[date, datetime] = {}
    for snapshot_date, snapshot_time in snapshots_by_day_time:
        latest_time_by_day[snapshot_date] = max(snapshot_time, latest_time_by_day.get(snapshot_date, snapshot_time))

    points: list[AtmOptionPoint] = []
    for snapshot_date in sorted(latest_time_by_day):
        snapshot_time = latest_time_by_day[snapshot_date]
        point = select_atm_option_pair(
            snapshots_by_day_time[(snapshot_date, snapshot_time)],
            as_of_date=snapshot_date,
            target_expiration=target_expiration,
            target_days_to_expiration=target_days_to_expiration,
            min_days_to_expiration=min_days_to_expiration,
        )
        if point is not None:
            points.append(point)

    changes: list[AtmOptionDailyChange] = []
    previous: AtmOptionPoint | None = None
    for point in points:
        changes.append(
            AtmOptionDailyChange(
                point=point,
                underlying_change=_difference(point.underlying_price, previous.underlying_price if previous else None),
                strike_change=_difference(point.strike, previous.strike if previous else None),
                average_mark_iv_change=_difference(
                    point.average_mark_iv,
                    previous.average_mark_iv if previous else None,
                ),
                straddle_mark_price_change=_difference(
                    point.straddle_mark_price,
                    previous.straddle_mark_price if previous else None,
                ),
            )
        )
        previous = point

    return changes


def write_option_quotes_csv(path: str | Path, quotes: Iterable[DeribitOptionQuote]) -> None:
    """Write option quotes to CSV, replacing any existing file."""

    with Path(path).open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for quote in quotes:
            writer.writerow(_quote_to_row(quote))


def append_option_snapshot_csv(path: str | Path, quotes: Iterable[DeribitOptionQuote]) -> None:
    """Append one snapshot to a CSV history file."""

    csv_path = Path(path)
    write_header = not csv_path.exists() or csv_path.stat().st_size == 0
    with csv_path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        if write_header:
            writer.writeheader()
        for quote in quotes:
            writer.writerow(_quote_to_row(quote))


def read_option_quotes_csv(path: str | Path) -> list[DeribitOptionQuote]:
    """Read option quotes previously written by this module."""

    with Path(path).open("r", newline="", encoding="utf-8") as file:
        return [_quote_from_row(row) for row in csv.DictReader(file)]


def _choose_expiration(
    quotes: Iterable[DeribitOptionQuote],
    *,
    snapshot_date: date,
    target_expiration: date | None,
    target_days_to_expiration: int | None,
    min_days_to_expiration: int,
) -> date | None:
    expirations = sorted({quote.expiration for quote in quotes})
    if target_expiration is not None:
        return target_expiration if target_expiration in expirations else None

    minimum_expiration = snapshot_date + timedelta(days=min_days_to_expiration)
    candidates = [expiration for expiration in expirations if expiration >= minimum_expiration]
    if not candidates:
        return None
    if target_days_to_expiration is None:
        return candidates[0]
    return min(candidates, key=lambda expiration: abs((expiration - snapshot_date).days - target_days_to_expiration))


def _quote_to_row(quote: DeribitOptionQuote) -> dict[str, str | float]:
    return {
        "snapshot_time": _ensure_utc(quote.snapshot_time).isoformat(),
        "instrument_name": quote.instrument_name,
        "expiration": quote.expiration.isoformat(),
        "strike": quote.strike,
        "option_type": quote.option_type,
        "underlying_price": _csv_number(quote.underlying_price),
        "mark_iv": _csv_number(quote.mark_iv),
        "mark_price": _csv_number(quote.mark_price),
        "bid_price": _csv_number(quote.bid_price),
        "ask_price": _csv_number(quote.ask_price),
        "mid_price": _csv_number(quote.mid_price),
        "open_interest": _csv_number(quote.open_interest),
        "volume": _csv_number(quote.volume),
    }


def _quote_from_row(row: dict[str, str]) -> DeribitOptionQuote:
    return DeribitOptionQuote(
        snapshot_time=_parse_datetime(row["snapshot_time"]),
        instrument_name=row["instrument_name"],
        expiration=date.fromisoformat(row["expiration"]),
        strike=float(row["strike"]),
        option_type=row["option_type"],
        underlying_price=_optional_float(row.get("underlying_price")),
        mark_iv=_optional_float(row.get("mark_iv")),
        mark_price=_optional_float(row.get("mark_price")),
        bid_price=_optional_float(row.get("bid_price")),
        ask_price=_optional_float(row.get("ask_price")),
        mid_price=_optional_float(row.get("mid_price")),
        open_interest=_optional_float(row.get("open_interest")),
        volume=_optional_float(row.get("volume")),
    )


def _date_from_timestamp(value: Any) -> date | None:
    number = _optional_float(value)
    if number is None:
        return None
    return datetime.fromtimestamp(number / 1000.0, tz=timezone.utc).date()


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_datetime(value: str) -> datetime:
    return _ensure_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _csv_number(value: float | None) -> str | float:
    return "" if value is None else value


def _first_option(quotes: Iterable[DeribitOptionQuote], option_type: str) -> DeribitOptionQuote | None:
    return next((quote for quote in quotes if quote.option_type == option_type), None)


def _field(quote: DeribitOptionQuote | None, field_name: str) -> float | None:
    if quote is None:
        return None
    return getattr(quote, field_name)


def _average_present(values: Iterable[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return sum(present) / len(present)


def _sum_present(values: Iterable[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return sum(present)


def _difference(value: float | None, previous: float | None) -> float | None:
    if value is None or previous is None:
        return None
    return value - previous
