import argparse
import urllib.request
from datetime import datetime, timezone

from rmi.brief import render_brief
from rmi.feeds import collect_quotes
from rmi.watchlist import load_watchlist


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a research-only market brief from public quotes. Does not trade."
    )
    parser.add_argument("--watchlist", required=True, help="Path to a watchlist JSON file")
    parser.add_argument("--out", help="Write the brief to this path as well as stdout")
    parser.add_argument(
        "--now",
        help="Override the clock with an ISO-8601 timestamp (used by tests)",
    )
    args = parser.parse_args(argv)
    watchlist = load_watchlist(args.watchlist)
    code, text = run(watchlist, now=_parse_now(args.now))
    print(text, end="")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
    return code


def run(watchlist, now: datetime, opener=urllib.request.urlopen, timeout=20):
    quotes = collect_quotes(watchlist.instruments, opener=opener, timeout=timeout)
    text = render_brief(watchlist, quotes, now)
    failed = not quotes or all(quote.error for quote in quotes)
    return (1 if failed else 0), text


def _parse_now(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed
