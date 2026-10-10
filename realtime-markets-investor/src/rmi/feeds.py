"""Public quote fetchers. No brokerage clients and no API keys."""

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal

from rmi.models import Instrument, Quote, ReferencePrint

USER_AGENT = "realtime-markets-investor/0.1 (research-only)"
YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
COINGECKO_PRICE = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids={coin_id}&vs_currencies={vs}&include_24hr_change=true&include_last_updated_at=true"
)
FRANKFURTER_LATEST = "https://api.frankfurter.app/latest?from={base}&to={quote}"


class FeedError(Exception):
    pass


def collect_quotes(instruments, opener=urllib.request.urlopen, timeout=20):
    return tuple(fetch_instrument(item, opener=opener, timeout=timeout) for item in instruments)


def fetch_instrument(instrument: Instrument, opener=urllib.request.urlopen, timeout=20) -> Quote:
    try:
        if instrument.feed == "yahoo_chart":
            quote = fetch_yahoo(instrument, opener=opener, timeout=timeout)
        elif instrument.feed == "coingecko":
            quote = fetch_coingecko(instrument, opener=opener, timeout=timeout)
        else:
            raise FeedError(f"unknown feed {instrument.feed!r}")
    except FeedError as exc:
        quote = Quote(
            instrument_id=instrument.id,
            sleeve=instrument.sleeve,
            name=instrument.name,
            role=instrument.role,
            source=instrument.feed,
            source_url="",
            error=str(exc),
        )

    if instrument.reference_feed == "frankfurter":
        quote.extra_references.append(
            fetch_frankfurter(instrument, opener=opener, timeout=timeout)
        )
    elif instrument.reference_feed:
        quote.extra_references.append(
            ReferencePrint(
                source=instrument.reference_feed,
                source_url="",
                label="reference feed",
                value=None,
                currency=None,
                as_of_date=None,
                error=f"unknown reference feed {instrument.reference_feed!r}",
            )
        )
    return quote


def fetch_yahoo(instrument: Instrument, opener, timeout) -> Quote:
    if not instrument.symbol:
        raise FeedError("yahoo_chart instrument is missing symbol")
    url = YAHOO_CHART.format(symbol=urllib.parse.quote(instrument.symbol, safe="=^"))
    payload = _get_json(url, opener=opener, timeout=timeout)
    return parse_yahoo_chart(payload, instrument, source_url=url)


def fetch_coingecko(instrument: Instrument, opener, timeout) -> Quote:
    if not instrument.coin_id or not instrument.vs_currency:
        raise FeedError("coingecko instrument is missing coin_id or vs_currency")
    url = COINGECKO_PRICE.format(
        coin_id=urllib.parse.quote(instrument.coin_id),
        vs=urllib.parse.quote(instrument.vs_currency),
    )
    payload = _get_json(url, opener=opener, timeout=timeout)
    return parse_coingecko(payload, instrument, source_url=url)


def fetch_frankfurter(instrument: Instrument, opener, timeout) -> ReferencePrint:
    base = instrument.frankfurter_from
    quote = instrument.frankfurter_to
    if not base or not quote:
        return ReferencePrint(
            source="frankfurter",
            source_url="",
            label="ECB reference rate via Frankfurter",
            value=None,
            currency=None,
            as_of_date=None,
            error="frankfurter pair is incomplete",
        )
    url = FRANKFURTER_LATEST.format(
        base=urllib.parse.quote(base),
        quote=urllib.parse.quote(quote),
    )
    try:
        payload = _get_json(url, opener=opener, timeout=timeout)
    except FeedError as exc:
        return ReferencePrint(
            source="frankfurter",
            source_url=url,
            label="ECB reference rate via Frankfurter",
            value=None,
            currency=quote,
            as_of_date=None,
            error=str(exc),
        )
    return parse_frankfurter(payload, source_url=url, quote=quote)


def parse_yahoo_chart(payload: dict, instrument: Instrument, source_url: str) -> Quote:
    chart = payload.get("chart") or {}
    if chart.get("error"):
        raise FeedError(f"yahoo chart error: {chart['error']}")
    results = chart.get("result") or []
    if not results:
        raise FeedError("yahoo chart returned no result")
    meta = results[0].get("meta") or {}
    market_time = None
    raw_time = meta.get("regularMarketTime")
    if isinstance(raw_time, (int, Decimal)) and not isinstance(raw_time, bool):
        market_time = datetime.fromtimestamp(int(raw_time), tz=timezone.utc)

    change_field = None
    feed_change_percent = None
    for field_name in ("fulldayChangePercent", "regularMarketChangePercent"):
        if meta.get(field_name) is not None:
            change_field = field_name
            feed_change_percent = _decimal(meta[field_name])
            break

    return Quote(
        instrument_id=instrument.id,
        sleeve=instrument.sleeve,
        name=meta.get("shortName") or instrument.name,
        role=instrument.role,
        source="Yahoo Finance chart (public, unofficial, may be delayed)",
        source_url=source_url,
        currency=_text(meta.get("currency")),
        last=_optional_decimal(meta.get("regularMarketPrice")),
        reference_value=_optional_decimal(meta.get("chartPreviousClose")),
        reference_field="chartPreviousClose" if meta.get("chartPreviousClose") is not None else None,
        feed_change=_optional_decimal(meta.get("fulldayChange")),
        feed_change_percent=feed_change_percent,
        feed_change_field=change_field,
        volume=_optional_decimal(meta.get("regularMarketVolume")),
        exchange_name=_text(meta.get("exchangeName")),
        market_time=market_time,
    )


def parse_coingecko(payload: dict, instrument: Instrument, source_url: str) -> Quote:
    vs = (instrument.vs_currency or "").lower()
    coin = payload.get(instrument.coin_id) if instrument.coin_id else None
    if not isinstance(coin, dict):
        raise FeedError(f"coingecko returned no price for {instrument.coin_id}")
    updated = coin.get("last_updated_at")
    market_time = None
    if isinstance(updated, (int, Decimal)) and not isinstance(updated, bool):
        market_time = datetime.fromtimestamp(int(updated), tz=timezone.utc)
    change_key = f"{vs}_24h_change"
    return Quote(
        instrument_id=instrument.id,
        sleeve=instrument.sleeve,
        name=instrument.name,
        role=instrument.role,
        source="CoinGecko simple price (public, unauthenticated, may be delayed)",
        source_url=source_url,
        currency=vs.upper() if vs else None,
        last=_optional_decimal(coin.get(vs)),
        feed_change_percent=_optional_decimal(coin.get(change_key)),
        feed_change_field=change_key if coin.get(change_key) is not None else None,
        market_time=market_time,
    )


def parse_frankfurter(payload: dict, source_url: str, quote: str) -> ReferencePrint:
    rates = payload.get("rates") or {}
    if quote not in rates:
        return ReferencePrint(
            source="Frankfurter",
            source_url=source_url,
            label="ECB reference rate via Frankfurter (not a tradable spot)",
            value=None,
            currency=quote,
            as_of_date=_text(payload.get("date")),
            error=f"frankfurter response has no {quote} rate",
        )
    return ReferencePrint(
        source="Frankfurter",
        source_url=source_url,
        label="ECB reference rate via Frankfurter (not a tradable spot)",
        value=_optional_decimal(rates.get(quote)),
        currency=quote,
        as_of_date=_text(payload.get("date")),
    )


def _get_json(url: str, opener, timeout: int) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with opener(request, timeout=timeout) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        raise FeedError(f"HTTP {exc.code} from {url.split('?', 1)[0]}") from exc
    except urllib.error.URLError as exc:
        raise FeedError(f"network error for {url.split('?', 1)[0]}: {exc.reason}") from exc
    except TimeoutError as exc:
        raise FeedError(f"timeout for {url.split('?', 1)[0]}") from exc
    try:
        return json.loads(body.decode("utf-8"), parse_float=Decimal)
    except json.JSONDecodeError as exc:
        raise FeedError(f"invalid JSON from {url.split('?', 1)[0]}") from exc


def _optional_decimal(value):
    if value is None:
        return None
    return _decimal(value)


def _decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _text(value):
    if value is None:
        return None
    return str(value)
