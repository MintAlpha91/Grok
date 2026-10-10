import json
import unittest
import urllib.error
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from rmi.brief import computed_change_percent, render_brief
from rmi.cli import run
from rmi.feeds import parse_coingecko, parse_frankfurter, parse_yahoo_chart
from rmi.models import Instrument
from rmi.policy import OutOfScope, place_order
from rmi.watchlist import load_watchlist

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 10, 6, 1, 30, tzinfo=timezone.utc)


class _Response:
    def __init__(self, payload: bytes):
        self.payload = payload

    def read(self):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class _Opener:
    def __init__(self, routes):
        self.routes = routes

    def __call__(self, request, timeout):
        url = request.full_url
        for needle, payload in self.routes.items():
            if needle in url:
                if isinstance(payload, Exception):
                    raise payload
                if callable(payload):
                    payload = payload()
                    if isinstance(payload, Exception):
                        raise payload
                return _Response(payload)
        raise urllib.error.URLError(f"unexpected url {url}")


def _instrument(**kwargs):
    defaults = dict(
        id="TEST",
        sleeve="equities",
        name="Test",
        role="example_not_a_holding",
        feed="yahoo_chart",
    )
    defaults.update(kwargs)
    return Instrument(**defaults)


class FeedParseTests(unittest.TestCase):
    def test_yahoo_reports_feed_fields_and_does_not_rename_them(self):
        payload = json.loads((FIXTURES / "yahoo_bhp.json").read_text(), parse_float=Decimal)
        quote = parse_yahoo_chart(payload, _instrument(id="TEST.AX"), source_url="https://example.test/yahoo")
        self.assertEqual(quote.last, Decimal("12.5"))
        self.assertEqual(quote.reference_field, "chartPreviousClose")
        self.assertEqual(quote.reference_value, Decimal("10"))
        self.assertEqual(quote.feed_change_percent, Decimal("25"))
        self.assertEqual(quote.feed_change_field, "fulldayChangePercent")
        self.assertIsNone(quote.error)

    def test_yahoo_error_has_no_invented_last(self):
        with self.assertRaises(Exception):
            parse_yahoo_chart({"chart": {"result": [], "error": None}}, _instrument(), "https://example.test")

    def test_coingecko_uses_only_returned_change(self):
        payload = json.loads((FIXTURES / "coingecko_btc.json").read_text(), parse_float=Decimal)
        quote = parse_coingecko(
            payload,
            _instrument(id="BTC-USD", sleeve="crypto", feed="coingecko", coin_id="bitcoin", vs_currency="usd"),
            source_url="https://example.test/cg",
        )
        self.assertEqual(quote.last, Decimal("20"))
        self.assertEqual(quote.feed_change_field, "usd_24h_change")
        self.assertEqual(quote.feed_change_percent, Decimal("1.5"))
        self.assertIsNone(quote.reference_value)

    def test_frankfurter_keeps_feed_date(self):
        payload = json.loads((FIXTURES / "frankfurter_audusd.json").read_text(), parse_float=Decimal)
        ref = parse_frankfurter(payload, source_url="https://example.test/fx", quote="USD")
        self.assertEqual(ref.value, Decimal("0.5"))
        self.assertEqual(ref.as_of_date, "2026-01-02")
        self.assertIn("not a tradable spot", ref.label)

    def test_computed_percent_is_arithmetic_only(self):
        self.assertEqual(computed_change_percent(Decimal("12.5"), Decimal("10")), Decimal("25.0000"))
        self.assertIsNone(computed_change_percent(Decimal("1"), Decimal("0")))


class BriefTests(unittest.TestCase):
    def test_fixture_run_labels_smsf_brisbane_and_omits_missing_numbers(self):
        watchlist = load_watchlist(Path(__file__).parents[1] / "watchlist.example.json")
        opener = _Opener(
            {
                "finance.yahoo.com": (FIXTURES / "yahoo_bhp.json").read_bytes(),
                "coingecko": (FIXTURES / "coingecko_btc.json").read_bytes(),
                "frankfurter": (FIXTURES / "frankfurter_audusd.json").read_bytes(),
            }
        )
        code, text = run(watchlist, now=NOW, opener=opener)
        self.assertEqual(code, 0)
        self.assertIn("Australia/Brisbane", text)
        self.assertIn("SMSF", text)
        self.assertIn("not personal cash", text)
        self.assertIn("example_not_a_holding", text)
        self.assertIn("2026-01-02", text)
        self.assertIn("not a tradable spot", text)
        self.assertIn("Out of scope", text)
        self.assertNotIn("Order submitted", text)
        self.assertIn("Last: 12.5 AUD", text)
        self.assertIn("Last: 20 USD", text)

    def test_failed_feeds_do_not_invent_prices(self):
        watchlist = load_watchlist(Path(__file__).parents[1] / "watchlist.example.json")
        opener = _Opener(
            {
                "finance.yahoo.com": lambda: urllib.error.HTTPError(
                    "https://example.test", 503, "down", hdrs=None, fp=None
                ),
                "coingecko": lambda: urllib.error.HTTPError(
                    "https://example.test", 503, "down", hdrs=None, fp=None
                ),
                "frankfurter": lambda: urllib.error.HTTPError(
                    "https://example.test", 503, "down", hdrs=None, fp=None
                ),
            }
        )
        code, text = run(watchlist, now=NOW, opener=opener)
        self.assertEqual(code, 1)
        self.assertIn("feed error", text)
        self.assertIn("Last: not available", text)
        self.assertNotIn("Last: 0", text)

    def test_render_empty_watchlist(self):
        from rmi.models import AccountContext, Watchlist

        watchlist = Watchlist(
            timezone="Australia/Brisbane",
            account=AccountContext("smsf", "Stake", "SMSF property, not personal cash."),
            instruments=(),
        )
        text = render_brief(watchlist, (), NOW)
        self.assertIn("No instruments were configured", text)
        self.assertIn("Australia/Brisbane", text)


class PolicyTests(unittest.TestCase):
    def test_place_order_cannot_trade(self):
        with self.assertRaises(OutOfScope):
            place_order(symbol="BHP.AX", side="buy", quantity=1)


if __name__ == "__main__":
    unittest.main()
