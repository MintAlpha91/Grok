"""Demo, PayID, and Stripe checkout for Rogers Inc Designs.

Australia can pay by PayID, and by card when STRIPE_SECRET_KEY is set.
Overseas addresses pay by Stripe Checkout. A missing key hides the card option.
Demo never charges and never prints.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import time
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


def _secret(env: dict) -> str:
    return (env.get("STRIPE_SECRET_KEY") or "").strip()


def card_available(env: dict | None = None) -> bool:
    env = os.environ if env is None else env
    return _secret(env).startswith(("sk_test_", "sk_live_", "rk_test_", "rk_live_"))


def warn_stripe_secret(env: dict | None = None) -> None:
    """A pk_ key in the secret slot leaves card checkout off. Say so at startup."""
    env = os.environ if env is None else env
    secret = _secret(env)
    if not secret.startswith("pk_"):
        return
    logging.getLogger("store").warning(
        "STRIPE_SECRET_KEY starts with pk_. That is a Stripe publishable key, not the secret key. "
        "Card checkout stays off. Put sk_test_ or sk_live_ in STRIPE_SECRET_KEY, "
        "and put this pk_ value in STRIPE_PUBLISHABLE_KEY."
    )


def payid_available(env: dict | None = None) -> bool:
    env = os.environ if env is None else env
    return bool((env.get("SHOP_PAYID") or "").strip())


def checkout_mode(env: dict | None = None) -> str:
    """Australian default. Card is a separate flag so PayID stays available."""
    env = os.environ if env is None else env
    if payid_available(env):
        return "payid"
    if card_available(env):
        return "stripe"
    if env.get("SHOP_CHECKOUT") == "demo":
        return "demo"
    return "off"


def require_secret(secret: str) -> str:
    """Hosted Checkout accepts a Stripe test or live secret."""
    secret = (secret or "").strip()
    if secret.startswith(("sk_test_", "sk_live_", "rk_test_", "rk_live_")):
        return secret
    raise ShopError("Set STRIPE_SECRET_KEY to a Stripe secret key (sk_test_… or sk_live_…).", 409)


def checkout_public(env: dict | None = None) -> dict:
    env = os.environ if env is None else env
    copy = load_copy()["checkout"]
    mode = checkout_mode(env)
    public = {
        "mode": mode,
        "card": card_available(env),
        "payid_available": payid_available(env),
        "stripe": copy["stripe"],
        "payid": copy["payid"],
        "demo_lead": copy["demo_lead"],
        "demo_emphasis": copy["demo_emphasis"],
        "demo_tail": copy["demo_tail"],
        "international": copy["international"],
        "off": copy["off"],
        "etsy_listing_url": load_copy()["etsy_listing_url"],
    }
    publishable = (env.get("STRIPE_PUBLISHABLE_KEY") or "").strip()
    if publishable.startswith(("pk_test_", "pk_live_")):
        public["publishable_key"] = publishable
    return public


def resolve_payment(customer: dict, requested: object, env: dict) -> str:
    """Australia defaults to PayID. Overseas addresses must use card."""
    choice = str(requested or "").strip().lower()
    if choice == "stripe":
        choice = "card"
    country = customer.get("country") or "AU"
    if country != "AU":
        if not card_available(env):
            raise ShopError("Overseas orders pay by card. Card checkout is not switched on.", 409)
        if choice not in {"", "card"}:
            raise ShopError("Overseas orders pay by card.", 409)
        return "stripe"
    if choice == "card":
        if not card_available(env):
            raise ShopError("Card payment is not switched on.", 409)
        return "stripe"
    if choice in {"", "payid"} and payid_available(env):
        return "payid"
    if card_available(env) and not payid_available(env):
        return "stripe"
    if payid_available(env):
        return "payid"
    if env.get("SHOP_CHECKOUT") == "demo":
        return "demo"
    raise ShopError(load_copy()["checkout"]["off"], 409)


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
    if order.get("tracking_number"):
        view["tracking_number"] = order["tracking_number"]
        view["tracking_url"] = order.get("tracking_url") or ""
        view["tracking_carrier"] = order.get("tracking_carrier") or ""
    return view


def _write(orders_dir: Path, order: dict) -> dict:
    orders_dir.mkdir(parents=True, exist_ok=True)
    if not ORDER_ID.match(order["id"]):
        raise ShopError("Bad order id.", 500)
    path = orders_dir / f"{order['id']}.json"
    path.write_text(json.dumps(order, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return order


def _commit_new_order(orders_dir: Path, order: dict) -> dict:
    saved = _write(orders_dir, order)
    try:
        from store.mail import notify_new_order_later

        notify_new_order_later(saved)
    except Exception as exc:
        logging.getLogger("store").warning("order email failed: %s", exc)
    return saved


_IDEMPOTENCY_KEY = re.compile(r"^[A-Za-z0-9_-]{8,80}$")


def normalize_idempotency_key(value: object) -> str:
    key = str(value or "").strip()
    if not key:
        return ""
    if not _IDEMPOTENCY_KEY.match(key):
        raise ShopError("That checkout key is not valid.")
    return key


def _idempotency_path(orders_dir: Path, key: str) -> Path:
    return orders_dir / "idempotency" / f"{key}.json"


def begin_idempotency(orders_dir: Path, key: str) -> dict | None:
    """Claim a checkout key. An existing order means this click is a repeat."""
    if not key:
        return None
    path = _idempotency_path(orders_dir, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(25):
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                data = {}
            order_id = str(data.get("order_id") or "")
            if ORDER_ID.match(order_id):
                try:
                    return load_order(orders_dir, order_id)
                except ShopError:
                    path.unlink(missing_ok=True)
                    continue
            time.sleep(0.05)
            continue
        os.write(fd, b'{"status": "pending"}\n')
        os.close(fd)
        return None
    raise ShopError("That checkout is already being placed.", 409)


def finish_idempotency(orders_dir: Path, key: str, order_id: str) -> None:
    if not key:
        return
    path = _idempotency_path(orders_dir, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"status": "done", "order_id": order_id}) + "\n", encoding="utf-8")


def release_idempotency(orders_dir: Path, key: str) -> None:
    if not key:
        return
    path = _idempotency_path(orders_dir, key)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if data.get("status") == "pending":
        path.unlink(missing_ok=True)


def load_order(orders_dir: Path, order_id: str) -> dict:
    if not ORDER_ID.match(order_id):
        raise ShopError("Unknown order.", 404)
    path = orders_dir / f"{order_id}.json"
    if not path.is_file():
        raise ShopError("Unknown order.", 404)
    return json.loads(path.read_text(encoding="utf-8"))


def _view_order(order: dict) -> dict:
    view = buyer_view(order)
    if order.get("stripe_url"):
        view["url"] = order["stripe_url"]
    return view


def place_order(
    orders_dir: Path,
    raw_lines: list,
    raw_customer: object,
    *,
    base_url: str,
    payment: object = None,
    idempotency_key: object = None,
    env: dict | None = None,
) -> dict:
    env = os.environ if env is None else env
    lines = _price_request(raw_lines)
    customer = validate_customer(raw_customer)
    mode = resolve_payment(customer, payment, env)
    postage = None
    if customer["country"] != "AU":
        from store.printful import quote_postage

        postage = quote_postage(lines, customer, env)
        settled = settle(lines, customer["country"], shipping_cents=postage["cents"])
    else:
        settled = settle(lines, "AU")
    key = normalize_idempotency_key(idempotency_key)
    existing = begin_idempotency(orders_dir, key)
    if existing:
        return _view_order(existing)
    now = _now()
    order = {
        "id": _new_id(),
        "created_brisbane": now.strftime("%Y-%m-%d %H:%M"),
        "mode": mode,
        "status": mode,
        "currency": "AUD",
        "lines": lines,
        "shipping_cents": settled["shipping_cents"],
        "shipping_name": (postage or {}).get("name") or ("Free shipping in Australia" if customer["country"] == "AU" else ""),
        "goods_cents": settled["goods_cents"],
        "gst_cents": settled["gst_cents"],
        "gst_included": settled["gst_included"],
        "total_cents": settled["total_cents"],
        "customer": customer,
        "payment_taken": False,
        "print_or_ship": False,
        "automatic_print": False,
        "notice": _notice(mode),
        "internal_note": load_copy()["fulfillment_note"],
        "fulfillment_hold": "demo" if mode == "demo" else "unpaid",
    }
    if key:
        order["idempotency_key"] = key
    if postage:
        order["printful_shipping"] = postage["id"]
    try:
        if mode == "demo":
            _commit_new_order(orders_dir, order)
            finish_idempotency(orders_dir, key, order["id"])
            return buyer_view(order)
        if mode == "payid":
            order["status"] = "awaiting_payment"
            order["payid"] = env["SHOP_PAYID"]
            order["payid_name"] = env.get("SHOP_PAYID_NAME") or "Rogers Inc Designs"
            _commit_new_order(orders_dir, order)
            finish_idempotency(orders_dir, key, order["id"])
            return buyer_view(order)
        session = create_stripe_session(order, base_url, require_secret(env.get("STRIPE_SECRET_KEY", "")))
        order["status"] = "pending_payment"
        order["stripe_session_id"] = session["id"]
        order["stripe_url"] = session["url"]
        _commit_new_order(orders_dir, order)
        finish_idempotency(orders_dir, key, order["id"])
        return _view_order(order)
    except Exception:
        release_idempotency(orders_dir, key)
        raise


def line_summary(line: dict) -> str:
    parts = [line.get("listing_name") or line.get("name") or "Tee", line.get("fabric_label") or ""]
    if line.get("size"):
        parts.append(str(line["size"]))
    return " — ".join(part for part in parts if part)


def stripe_fields(order: dict, base_url: str) -> list[tuple[str, str]]:
    """AUD Checkout Session. Australia ships free. Overseas postage is a charged rate, never zero."""
    origin = base_url.rstrip("/")
    country = (order.get("customer") or {}).get("country") or "AU"
    shipping_cents = int(order.get("shipping_cents") or 0)
    shipping_name = order.get("shipping_name") or (
        "Free shipping in Australia" if country == "AU" else "International postage"
    )
    fields = [
        ("mode", "payment"),
        ("customer_email", order["customer"]["email"]),
        ("client_reference_id", order["id"]),
        ("success_url", f"{origin}/order/{order['id']}?session_id={{CHECKOUT_SESSION_ID}}"),
        ("cancel_url", f"{origin}/checkout?cancelled=1"),
        ("metadata[order_id]", order["id"]),
        ("metadata[gst]", "included" if country == "AU" else "export"),
        ("metadata[shipping]", country),
        ("automatic_tax[enabled]", "false"),
        ("shipping_options[0][shipping_rate_data][type]", "fixed_amount"),
        ("shipping_options[0][shipping_rate_data][display_name]", shipping_name),
        ("shipping_options[0][shipping_rate_data][fixed_amount][amount]", str(shipping_cents if country != "AU" else 0)),
        ("shipping_options[0][shipping_rate_data][fixed_amount][currency]", "aud"),
        ("shipping_options[0][shipping_rate_data][tax_behavior]", "inclusive"),
    ]
    if country == "AU":
        fields.append(("shipping_address_collection[allowed_countries][0]", "AU"))
    for index, line in enumerate(order["lines"]):
        prefix = f"line_items[{index}]"
        fields.extend(
            [
                (f"{prefix}[quantity]", str(line["qty"])),
                (f"{prefix}[price_data][currency]", "aud"),
                (f"{prefix}[price_data][unit_amount]", str(line["unit_cents"])),
                (f"{prefix}[price_data][tax_behavior]", "inclusive"),
                (f"{prefix}[price_data][product_data][name]", line_summary(line)),
                (
                    f"{prefix}[price_data][product_data][description]",
                    "GST included." if country == "AU" else "Australian shelf price.",
                ),
                (f"{prefix}[price_data][product_data][metadata][fabric]", line.get("fabric_label") or ""),
                (f"{prefix}[price_data][product_data][metadata][size]", line.get("size") or ""),
            ]
        )
    return fields


def _form_body(fields: list[tuple[str, str]]) -> bytes:
    """Encode Checkout params. Stripe must see the success placeholder unencoded."""
    parts = []
    for key, value in fields:
        encoded_key = urllib.parse.quote(str(key), safe="")
        if "{CHECKOUT_SESSION_ID}" in value:
            token = "___CHECKOUT_SESSION_ID___"
            swapped = value.replace("{CHECKOUT_SESSION_ID}", token)
            encoded = urllib.parse.quote(swapped, safe="").replace(token, "{CHECKOUT_SESSION_ID}")
        else:
            encoded = urllib.parse.quote(str(value), safe="")
        parts.append(f"{encoded_key}={encoded}")
    return "&".join(parts).encode()


def _stripe_request(path: str, secret: str, fields: list[tuple[str, str]] | None = None) -> dict:
    data = None if fields is None else _form_body(fields)
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
    secret = require_secret(secret)
    session = _stripe_request("checkout/sessions", secret, stripe_fields(order, base_url))
    if not session.get("url") or not session.get("id"):
        raise ShopError("Card checkout did not return a payment page.", 502)
    return session


def apply_paid_session(orders_dir: Path, order_id: str, session: dict) -> dict:
    """Mark a paid Checkout Session and run the same Printful path as Mark paid."""
    order = load_order(orders_dir, order_id)
    session_id = session.get("id")
    if order.get("stripe_session_id") and session_id and order["stripe_session_id"] != session_id:
        raise ShopError("This payment session does not match the order.", 400)
    if session.get("payment_status") != "paid":
        return buyer_view(order)
    if order.get("printful_order_id") and order.get("payment_taken"):
        return buyer_view(order)
    currency = str(session.get("currency") or "").lower()
    if session.get("amount_total") != order["total_cents"] or currency != "aud":
        raise ShopError("Payment amount does not match this order.", 409)
    details = session.get("total_details") or {}
    shipping = details.get("amount_shipping")
    paid_country = ((session.get("shipping_details") or {}).get("address") or {}).get("country")
    order_country = (order.get("customer") or {}).get("country") or "AU"
    if order_country == "AU":
        if shipping not in (None, 0) or (paid_country and paid_country != "AU"):
            raise ShopError("Payment shipping does not match free Australian delivery.", 409)
    else:
        if paid_country and paid_country != order_country:
            raise ShopError("Payment country does not match this order.", 409)
        if shipping not in (None, order.get("shipping_cents")):
            raise ShopError("Payment postage does not match this order.", 409)
    from store.printful import mark_order_paid

    mark_order_paid(orders_dir, order_id)
    return buyer_view(load_order(orders_dir, order_id))


def confirm_stripe(orders_dir: Path, order_id: str, session_id: str, secret: str) -> dict:
    secret = require_secret(secret)
    order = load_order(orders_dir, order_id)
    if order.get("stripe_session_id") != session_id:
        raise ShopError("This payment session does not match the order.", 400)
    if order.get("payment_taken") and order.get("printful_order_id"):
        return buyer_view(order)
    session = _stripe_request(f"checkout/sessions/{urllib.parse.quote(session_id)}", secret)
    return apply_paid_session(orders_dir, order_id, session)


def verify_stripe_signature(payload: bytes, header: str, secret: str, tolerance: int = 300) -> bool:
    if not secret or not header or not payload:
        return False
    parts: dict[str, list[str]] = {}
    for item in header.split(","):
        key, _, value = item.strip().partition("=")
        if key and value:
            parts.setdefault(key, []).append(value)
    timestamps = parts.get("t") or []
    signatures = parts.get("v1") or []
    if not timestamps or not signatures:
        return False
    try:
        stamp = int(timestamps[0])
    except ValueError:
        return False
    if abs(int(time.time()) - stamp) > tolerance:
        return False
    signed = f"{stamp}.".encode() + payload
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, candidate) for candidate in signatures)


def handle_stripe_webhook(orders_dir: Path, event: dict) -> dict:
    if not isinstance(event, dict) or event.get("type") != "checkout.session.completed":
        return {"ok": True, "ignored": True}
    session = (event.get("data") or {}).get("object") if isinstance(event.get("data"), dict) else None
    if not isinstance(session, dict):
        return {"ok": True, "ignored": True}
    if session.get("payment_status") != "paid":
        return {"ok": True, "pending": True}
    metadata = session.get("metadata") if isinstance(session.get("metadata"), dict) else {}
    order_id = str(metadata.get("order_id") or session.get("client_reference_id") or "")
    if not ORDER_ID.match(order_id):
        raise ShopError("Unknown order.", 404)
    view = apply_paid_session(orders_dir, order_id, session)
    return {"ok": True, "id": view["id"], "paid": view["payment_taken"]}
