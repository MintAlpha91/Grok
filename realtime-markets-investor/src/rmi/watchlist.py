import json
from pathlib import Path

from rmi.models import AccountContext, Instrument, Watchlist


def load_watchlist(path: str | Path) -> Watchlist:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    account = payload["account_context"]
    instruments = tuple(
        Instrument(
            id=item["id"],
            sleeve=item["sleeve"],
            name=item["name"],
            role=item.get("role", "unspecified"),
            feed=item["feed"],
            symbol=item.get("symbol"),
            coin_id=item.get("coin_id"),
            vs_currency=item.get("vs_currency"),
            reference_feed=item.get("reference_feed"),
            frankfurter_from=item.get("frankfurter_from"),
            frankfurter_to=item.get("frankfurter_to"),
        )
        for item in payload["instruments"]
    )
    return Watchlist(
        timezone=payload.get("timezone", "Australia/Brisbane"),
        account=AccountContext(
            type=account["type"],
            holder=account["holder"],
            note=account["note"],
        ),
        instruments=instruments,
    )
