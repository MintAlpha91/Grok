"""Render a research brief from quotes. Does not invent missing numbers."""

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from rmi.policy import OUT_OF_SCOPE, banner_lines

PERCENT_PLACES = Decimal("0.0001")


def render_brief(watchlist, quotes, now: datetime) -> str:
    zone = ZoneInfo(watchlist.timezone)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    local_now = now.astimezone(zone)
    lines = [
        "# Realtime markets research brief",
        "",
        f"**{banner_lines()[0]}**",
        "",
        f"- Shown in: {watchlist.timezone}",
        f"- Generated: {local_now.strftime('%Y-%m-%d %H:%M')} {watchlist.timezone}",
        f"- Account: {watchlist.account.type.upper()}. Holder named in the watchlist: {watchlist.account.holder}.",
        f"- Account note: {watchlist.account.note}",
        f"- {banner_lines()[1]}",
        f"- {banner_lines()[2]}",
        "- Mode: research-only",
        "",
    ]

    by_sleeve: dict[str, list] = {}
    for quote in quotes:
        by_sleeve.setdefault(quote.sleeve, []).append(quote)

    if not quotes:
        lines.append("No instruments were configured. Nothing was fetched.")
        lines.append("")

    for sleeve in _sleeve_order(by_sleeve):
        lines.append(f"## {sleeve}")
        lines.append("")
        for quote in by_sleeve[sleeve]:
            lines.extend(_quote_lines(quote, zone, local_now))
            lines.append("")

    lines.extend(
        [
            "## Risk rules",
            "",
            "1. Research and brief only. No orders, transfers, or position sizes.",
            "2. The Stake portfolio is SMSF property. Do not treat it as personal cash.",
            "3. Example symbols are not holdings and are not a portfolio.",
            "4. A feed percent and a computed percent are different numbers. Both are shown only when present. Neither is a target.",
            "5. Quote age is reported. No stale-data limit is active until Jason sets one.",
            "6. Crypto in the example watchlist does not mean the SMSF holds crypto or that it may.",
            "",
            "## Out of scope until Jason opts in",
            "",
        ]
    )
    for item in OUT_OF_SCOPE:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Decisions still open",
            "",
            "- Which sleeves stay in scope: equities, FX, crypto, or a subset.",
            "- Which symbols replace the example watchlist. Do not assume current SMSF holdings.",
            "- Alert thresholds. None are configured.",
            "- Whether a paid or brokerage market-data feed is wanted later.",
            "- Whether crypto research belongs in the SMSF workflow at all.",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def computed_change_percent(last: Decimal, reference: Decimal) -> Decimal | None:
    if reference == 0:
        return None
    return ((last - reference) / reference * Decimal(100)).quantize(PERCENT_PLACES, rounding=ROUND_HALF_UP)


def _quote_lines(quote, zone, local_now):
    lines = [
        f"### {quote.instrument_id} — {quote.name}",
        "",
        f"- Role: {quote.role}",
        f"- Sleeve: {quote.sleeve}",
    ]
    if quote.error:
        lines.append("- Status: feed error")
        lines.append(f"- Error: {quote.error}")
        lines.append("- Last: not available")
        lines.extend(_reference_lines(quote))
        return lines

    lines.append("- Status: quote returned")
    lines.append(f"- Source: {quote.source}")
    if quote.source_url:
        lines.append(f"- Source URL: {quote.source_url}")
    if quote.exchange_name:
        lines.append(f"- Exchange name from feed: {quote.exchange_name}")
    if quote.last is None:
        lines.append("- Last: not present in the feed response")
    else:
        lines.append(f"- Last: {_num(quote.last)} {quote.currency or ''}".rstrip())
    if quote.reference_value is not None and quote.reference_field:
        lines.append(
            f"- Reference `{quote.reference_field}` from the same response: {_num(quote.reference_value)} {quote.currency or ''}".rstrip()
        )
    if quote.last is not None and quote.reference_value is not None:
        change = computed_change_percent(quote.last, quote.reference_value)
        if change is None:
            lines.append("- Computed change vs that reference: not computed (reference was zero)")
        else:
            lines.append(
                f"- Computed change vs `{quote.reference_field}`: {_num(change)}% "
                "(arithmetic on those two fields, rounded half up to 4 decimal places; not a forecast)"
            )
    if quote.feed_change is not None:
        lines.append(f"- Feed-reported change (`fulldayChange`): {_num(quote.feed_change)} {quote.currency or ''}".rstrip())
    if quote.feed_change_percent is not None and quote.feed_change_field:
        lines.append(
            f"- Feed-reported percent (`{quote.feed_change_field}`): {_num(quote.feed_change_percent)}%"
        )
    if quote.volume is not None:
        lines.append(f"- Feed-reported volume (`regularMarketVolume`): {_num(quote.volume)}")
    if quote.market_time is not None:
        local_market = quote.market_time.astimezone(zone)
        age_minutes = int((local_now - local_market).total_seconds() // 60)
        lines.append(f"- Feed timestamp: {local_market.strftime('%Y-%m-%d %H:%M')} {zone.key}")
        lines.append(f"- Age at generation: {age_minutes} minutes")
        lines.append("- Stale threshold: none configured")
    lines.extend(_reference_lines(quote))
    return lines


def _reference_lines(quote):
    lines = []
    for ref in quote.extra_references:
        lines.append(f"- Additional print ({ref.label}):")
        lines.append(f"  - Source: {ref.source}")
        if ref.source_url:
            lines.append(f"  - Source URL: {ref.source_url}")
        if ref.error:
            lines.append(f"  - Error: {ref.error}")
            lines.append("  - Value: not available")
        elif ref.value is None:
            lines.append("  - Value: not present in the response")
        else:
            lines.append(f"  - Value: {_num(ref.value)} {ref.currency or ''}".rstrip())
        if ref.as_of_date:
            lines.append(f"  - Rate date from feed: {ref.as_of_date}")
        lines.append(
            "  - This print is shown beside the other quote for source comparison only. It is not an executable spread."
        )
    return lines


def _sleeve_order(by_sleeve):
    preferred = ("equities", "fx", "crypto")
    ordered = [name for name in preferred if name in by_sleeve]
    ordered.extend(sorted(name for name in by_sleeve if name not in preferred))
    return ordered


def _num(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text
