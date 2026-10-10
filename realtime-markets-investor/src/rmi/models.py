from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class Instrument:
    id: str
    sleeve: str
    name: str
    role: str
    feed: str
    symbol: str | None = None
    coin_id: str | None = None
    vs_currency: str | None = None
    reference_feed: str | None = None
    frankfurter_from: str | None = None
    frankfurter_to: str | None = None


@dataclass(frozen=True)
class AccountContext:
    type: str
    holder: str
    note: str


@dataclass(frozen=True)
class Watchlist:
    timezone: str
    account: AccountContext
    instruments: tuple[Instrument, ...]


@dataclass
class ReferencePrint:
    source: str
    source_url: str
    label: str
    value: Decimal | None
    currency: str | None
    as_of_date: str | None
    error: str | None = None


@dataclass
class Quote:
    instrument_id: str
    sleeve: str
    name: str
    role: str
    source: str
    source_url: str
    currency: str | None = None
    last: Decimal | None = None
    reference_value: Decimal | None = None
    reference_field: str | None = None
    feed_change: Decimal | None = None
    feed_change_percent: Decimal | None = None
    feed_change_field: str | None = None
    volume: Decimal | None = None
    exchange_name: str | None = None
    market_time: datetime | None = None
    error: str | None = None
    extra_references: list[ReferencePrint] = field(default_factory=list)
