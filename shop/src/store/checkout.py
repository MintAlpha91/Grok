"""Demo, PayID, and Stripe checkout for Rogers Inc Designs. Demo never charges and never prints."""

from __future__ import annotations

import json
import os
import re
import secrets
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from store.catalog import (
    ShopError,
    load_catalog,
    load_copy,
    price_addon,
    price_line,
    public_line,
    settle,
    validate_customer,
)

BRISBANE = ZoneInfo("Australia/Brisbane")
ORDER_ID = re.compile(r"^RID-[A-F0-9]{8}$")


def checkout_mode(env: dict | None = None) -> str:
    env = os.environ if env is None else env
    if env.get("STRIPE_SECRET_KEY"):
        return "stripe"
    if env.get("SHOP_PAYID"):
        return "payid"
    if env.get("SHOP_CHECKOUT") == "demo":
        return "demo"
    return "off"


def checkout_public(env: dict | None = None) -> dict:
    copy = load_copy()["checkout"]
    mode = checkout_mode(env)
    return {
        "mode": mode,
        "stripe": copy["stripe"],
        "payid": copy["payid"],
        "demo_lead": copy["demo_lead"],
        "demo_emphasis": copy["demo_emphasis"],
        "demo_tail": copy["demo_tail"],
        "international": copy["international"],
        "off": copy["off"],
        "etsy_listing_url": load_copy()["etsy_listing_url"],
    }


def _now() -> datetime:
    return datetime.now(BRISBANE)


def _new_id() -> str:
    return "RID-" + secrets.token_hex(4).upper()


def _price_request(raw_lines: list) -> list[dict]:
    if not isinstance(raw_lines, list) or not raw_lines:
        raise ShopError("Your cart is empty.")
    if len(raw_lines) > 12:
        raise ShopError("Too many lines in this order.")
    catalog = load_catalog()
    priced = []
    for raw in raw_lines:
        if not isinstance(raw, dict):
            raise ShopError("A cart line is unreadable.")
        qty = raw.get("qty")
        priced.append(
            price_line(
                catalog,
                str(raw.get("slug", "")),
                str(raw.get("fabric", "")),
                str(raw.get("size", "")),
                qty,
            )
        )
        addon_id = raw.get("addon")
        if addon_id:
            priced.append(price_addon(catalog, str(addon_id), qty, str(raw.get("slug", ""))))
    return priced


def _notice(mode: str) -> dict:
    copy = load_copy()["checkout"]
    if mode == "demo":
        return {
            "kind": "demo",
            "text": f"{copy['demo_lead']} {copy['demo_tail']}",
            "emphasis": copy["demo_emphasis"],
        }
    if mode == "payid":
        return {"kind": "payid", "text": copy["payid"], "emphasis": ""}
    if mode == "stripe":
        return {"kind": "stripe", "text": copy["stripe"], "emphasis": ""}
    return {"kind": "off", "text": copy["off"], "emphasis": ""}


def buyer_view(order: dict) -> dict:
    view = {
        "id": order["id"],
        "created_brisbane": order["created_brisbane"],
        "mode": order["mode"],
        "status": order["status"],
        "currency": order["currency"],
        "lines": [public_line(line) for line in order["lines"]],
        "shipping_cents": order["shipping_cents"],
        "total_cents": order["total_cents"],
        "gst_included": True,
        "gst_cents": order.get("gst_cents", 0),
        "customer": order["customer"],
        "payment_taken": order["payment_taken"],
        "print_or_ship": order["print_or_ship"],
        "automatic_print": False,
        "notice": order["notice"],
    }
    if order["mode"] == "payid":
        view["payid"] = order.get("payid")
        view["payid_name"] = order.get("payid_name")
        view["reference"] = order["id"]
    if order.get("stripe_url"):
        view["url"] = order["stripe_url"]
    return view


def _write(orders_dir: Path, order: dict) -> dict:
    orders_dir.mkdir(parents=True, exist_ok=True)
    if not ORDER_ID.match(order["id"]):
        raise ShopError("Bad order id.", 500)
    path = orders_dir / f"{order['id']}.json"
    path.write_text(json.dumps(order, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return order


def load_order(orders_dir: Path, order_id: str) -> dict:
    if not ORDER_ID.match(order_id):
        raise ShopError("Unknown order.", 404)
    path = orders_dir / f"{order_id}.json"
    if not path.is_file():
        raise ShopError("Unknown order.", 404)
    return json.loads(path.read_text(encoding="utf-8"))


def place_order(
    orders_dir: Path,
    raw_lines: list,
    raw_customer: object,
    *,
    base_url: str,
    env: dict | None = None,
) -> dict:
    env = os.environ if env is None else env
    mode = checkout_mode(env)
    if mode == "off":
        raise ShopError(load_copy()["checkout"]["off"], 409)
    lines = _price_request(raw_lines)
    customer = validate_customer(raw_customer)
    settled = settle(lines, customer["country"])
    now = _now()
    order = {
        "id": _new_id(),
        "created_brisbane": now.strftime("%Y-%m-%d %H:%M"),
        "mode": mode,
        "status": mode,
        "currency": "AUD",
        "lines": lines,
        "shipping_cents": settled["shipping_cents"],
        "goods_cents": settled["goods_cents"],
        "gst_cents": settled["gst_cents"],
        "gst_included": True,
        "total_cents": settled["total_cents"],
        "customer": customer,
        "payment_taken": False,
        "print_or_ship": False,
        "automatic_print": False,
        "notice": _notice(mode),
        "internal_note": load_copy()["fulfillment_note"],
        "fulfillment_hold": "demo" if mode == "demo" else "unpaid",
    }
    if mode == "demo":
        _write(orders_dir, order)
        return buyer_view(order)
    if mode == "payid":
        order["status"] = "awaiting_payment"
        order["payid"] = env["SHOP_PAYID"]
        order["payid_name"] = env.get("SHOP_PAYID_NAME") or "Rogers Inc Designs"
        _write(orders_dir, order)
        return buyer_view(order)
    session = create_stripe_session(order, base_url, env["STRIPE_SECRET_KEY"])
    order["status"] = "pending_payment"
    order["stripe_session_id"] = session["id"]
    order["stripe_url"] = session["url"]
    _write(orders_dir, order)
    view = buyer_view(order)
    view["url"] = session["url"]
    return view


def stripe_fields(order: dict, base_url: str) -> list[tuple[str, str]]:
    fields = [
        ("mode", "payment"),
        ("customer_email", order["customer"]["email"]),
        ("client_reference_id", order["id"]),
        ("success_url", f"{base_url}/order/{order['id']}?session_id={{CHECKOUT_SESSION_ID}}"),
        ("cancel_url", f"{base_url}/checkout?cancelled=1"),
        ("metadata[order_id]", order["id"]),
    ]
    for index, line in enumerate(order["lines"]):
        prefix = f"line_items[{index}]"
        name = f"{line['listing_name']} — {line['fabric_label']} — {line['size']}"
        fields.extend(
            [
                (f"{prefix}[quantity]", str(line["qty"])),
                (f"{prefix}[price_data][currency]", "aud"),
                (f"{prefix}[price_data][unit_amount]", str(line["unit_cents"])),
                (f"{prefix}[price_data][product_data][name]", name),
            ]
        )
    return fields


def _stripe_request(path: str, secret: str, fields: list[tuple[str, str]] | None = None) -> dict:
    data = None if fields is None else urllib.parse.urlencode(fields).encode()
    request = urllib.request.Request(
        f"https://api.stripe.com/v1/{path}",
        data=data,
        method="POST" if fields is not None else "GET",
        headers={"Authorization": f"Bearer {secret}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        message = "Card checkout could not start."
        try:
            message = json.loads(detail)["error"]["message"]
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
        raise ShopError(message, 502) from exc
    except urllib.error.URLError as exc:
        raise ShopError("Card checkout could not be reached.", 502) from exc


def create_stripe_session(order: dict, base_url: str, secret: str) -> dict:
    session = _stripe_request("checkout/sessions", secret, stripe_fields(order, base_url))
    if not session.get("url") or not session.get("id"):
        raise ShopError("Card checkout did not return a payment page.", 502)
    return session


def confirm_stripe(orders_dir: Path, order_id: str, session_id: str, secret: str) -> dict:
    order = load_order(orders_dir, order_id)
    if order.get("stripe_session_id") != session_id:
        raise ShopError("This payment session does not match the order.", 400)
    if order["status"] == "paid":
        return buyer_view(order)
    session = _stripe_request(f"checkout/sessions/{urllib.parse.quote(session_id)}", secret)
    if session.get("payment_status") != "paid":
        return buyer_view(order)
    if session.get("amount_total") != order["total_cents"] or session.get("currency") != "aud":
        raise ShopError("Payment amount does not match this order.", 409)
    order["status"] = "paid"
    order["payment_taken"] = True
    order["print_or_ship"] = False
    order["automatic_print"] = False
    order["fulfillment_hold"] = "ready_for_manual_print"
    _write(orders_dir, order)
    return buyer_view(order)
