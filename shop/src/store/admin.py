"""Password page for marking PayID orders paid. SHOP_ADMIN_PASSWORD is required."""

from __future__ import annotations

import hashlib
import hmac
import os
from html import escape
from pathlib import Path

from store.checkout import ORDER_ID
from store.printful import list_orders, mark_order_paid

COOKIE = "shop_admin"


def admin_password(env: dict | None = None) -> str:
    env = os.environ if env is None else env
    return (env.get("SHOP_ADMIN_PASSWORD") or "").strip()


def admin_token(password: str) -> str:
    return hmac.new(password.encode(), b"rogers-shop-admin", hashlib.sha256).hexdigest()


def password_matches(supplied: str, env: dict | None = None) -> bool:
    expected = admin_password(env)
    if not expected or not supplied:
        return False
    return hmac.compare_digest(supplied, expected)


def cookie_is_valid(header: str, env: dict | None = None) -> bool:
    expected = admin_password(env)
    if not expected:
        return False
    token = admin_token(expected)
    for part in (header or "").split(";"):
        name, _, value = part.strip().partition("=")
        if name == COOKIE and value and hmac.compare_digest(value, token):
            return True
    return False


def _money(cents: int) -> str:
    return f"AU${cents / 100:.2f}"


def _line(order: dict) -> str:
    parts = []
    for line in order.get("lines") or []:
        parts.append(
            f"{line.get('qty', 1)} × {line.get('listing_name') or line.get('slug')} · {line.get('size', '')}"
        )
    return "; ".join(parts)


def login_page(message: str = "") -> str:
    note = f"<p class='alert'>{escape(message)}</p>" if message else ""
    return f"""<!DOCTYPE html>
<html lang="en-AU">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex">
  <title>Shop admin — Rogers Inc Designs</title>
  <style>
    body {{ margin: 0; font: 16px/1.45 Outfit, sans-serif; background: #14110e; color: #f3eee6; }}
    main {{ max-width: 28rem; margin: 4rem auto; padding: 0 1rem; }}
    form {{ display: grid; gap: 0.75rem; }}
    input, button {{ font: inherit; padding: 0.6rem 0.7rem; }}
    button {{ background: #c4553a; color: white; border: 0; cursor: pointer; }}
    .alert {{ color: #ffb4a2; }}
  </style>
</head>
<body>
  <main>
    <h1>Shop admin</h1>
    <p>PayID orders stay unpaid until you mark them paid.</p>
    {note}
    <form method="post" action="/admin/login">
      <label>Password <input type="password" name="password" autocomplete="current-password" required></label>
      <button type="submit">Enter</button>
    </form>
  </main>
</body>
</html>
"""


def orders_page(orders_dir: Path, message: str = "") -> str:
    rows = []
    for order in list_orders(orders_dir):
        order_id = escape(str(order["id"]))
        customer = order.get("customer") or {}
        status = escape(str(order.get("status") or ""))
        printful = order.get("printful_order_id")
        printful_text = escape(str(printful)) if printful else escape(str(order.get("printful_status") or "not sent"))
        error = escape(str(order.get("printful_error") or ""))
        tracking = escape(str(order.get("tracking_number") or ""))
        button = ""
        if not printful:
            button = (
                f"<form method='post' action='/admin/orders/{order_id}/paid'>"
                "<button type='submit'>Mark paid</button></form>"
            )
        rows.append(
            "<tr>"
            f"<td>{order_id}</td>"
            f"<td>{escape(str(order.get('created_brisbane') or ''))}</td>"
            f"<td>{status}</td>"
            f"<td>{escape(str(customer.get('name') or ''))}<br>{escape(str(customer.get('email') or ''))}</td>"
            f"<td>{escape(_line(order))}</td>"
            f"<td>{_money(int(order.get('total_cents') or 0))}</td>"
            f"<td>{printful_text}</td>"
            f"<td>{tracking}</td>"
            f"<td>{error}{button}</td>"
            "</tr>"
        )
    note = f"<p class='alert'>{escape(message)}</p>" if message else ""
    body = "".join(rows) or "<tr><td colspan='9'>No orders yet.</td></tr>"
    return f"""<!DOCTYPE html>
<html lang="en-AU">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex">
  <title>Orders — Rogers Inc Designs</title>
  <style>
    body {{ margin: 0; font: 15px/1.4 Outfit, sans-serif; background: #14110e; color: #f3eee6; }}
    main {{ padding: 1.25rem; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid #3a332c; text-align: left; vertical-align: top; padding: 0.45rem; }}
    button {{ font: inherit; background: #c4553a; color: white; border: 0; padding: 0.4rem 0.6rem; cursor: pointer; }}
    .alert {{ color: #ffb4a2; }}
    a {{ color: #f3eee6; }}
  </style>
</head>
<body>
  <main>
    <h1>Orders</h1>
    <p>Mark paid after the PayID payment lands. That creates a Printful order (draft unless PRINTFUL_AUTO_CONFIRM=true).</p>
    {note}
    <table>
      <thead>
        <tr><th>Order</th><th>When</th><th>Status</th><th>Customer</th><th>Lines</th><th>Total</th><th>Printful</th><th>Tracking</th><th></th></tr>
      </thead>
      <tbody>{body}</tbody>
    </table>
    <p><a href="/admin/logout">Log out</a></p>
  </main>
</body>
</html>
"""


def mark_paid_from_admin(orders_dir: Path, order_id: str, env: dict | None = None) -> str:
    if not ORDER_ID.match(order_id):
        return "Unknown order."
    order = mark_order_paid(orders_dir, order_id, env)
    if order.get("printful_error"):
        return f"{order['id']} marked paid. Printful: {order['printful_error']}"
    if order.get("printful_order_id"):
        state = "confirmed" if order.get("printful_confirmed") else "draft"
        return f"{order['id']} marked paid. Printful order {order['printful_order_id']} ({state})."
    if order.get("printful_status") == "skipped":
        return f"{order['id']} marked paid. Printful was skipped because PRINTFUL_API_KEY is not set."
    return f"{order['id']} marked paid."
