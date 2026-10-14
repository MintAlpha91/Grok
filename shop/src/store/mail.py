"""Order mail. Missing SMTP settings are logged and skipped."""

from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

log = logging.getLogger("store")

DEFAULT_ALERT = "rogersinc426@gmail.com"


def alert_email(env: dict | None = None) -> str:
    env = os.environ if env is None else env
    return (env.get("SHOP_ALERT_EMAIL") or DEFAULT_ALERT).strip() or DEFAULT_ALERT


def _money(cents: int) -> str:
    return f"AU${cents / 100:.2f}"


def smtp_config(env: dict | None = None) -> dict | None:
    env = os.environ if env is None else env
    host = (env.get("SMTP_HOST") or "").strip()
    user = (env.get("SMTP_USER") or "").strip()
    password = env.get("SMTP_PASS") or ""
    sender = (env.get("SMTP_FROM") or user).strip()
    if not host or not sender:
        log.warning("email skipped: SMTP_HOST or SMTP_FROM is not set")
        return None
    if user and not str(password).strip():
        log.warning("email skipped: SMTP_USER is set without SMTP_PASS")
        return None
    try:
        port = int((env.get("SMTP_PORT") or "587").strip())
    except ValueError:
        log.warning("email skipped: SMTP_PORT is not a number")
        return None
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "sender": sender,
    }


def send_email(to: str, subject: str, body: str, env: dict | None = None) -> bool:
    cfg = smtp_config(env)
    if cfg is None or not to:
        return False
    message = EmailMessage()
    message["From"] = cfg["sender"]
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    try:
        if cfg["port"] == 465:
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=20) as smtp:
                if cfg["user"]:
                    smtp.login(cfg["user"], cfg["password"])
                smtp.send_message(message)
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=20) as smtp:
                smtp.ehlo()
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
                if cfg["user"]:
                    smtp.login(cfg["user"], cfg["password"])
                smtp.send_message(message)
    except Exception as exc:
        log.warning("email failed: %s", exc)
        return False
    return True


def _lines(order: dict) -> str:
    rows = []
    for line in order.get("lines") or []:
        rows.append(
            f"- {line.get('qty', 1)} × {line.get('listing_name') or line.get('name')} "
            f"({line.get('fabric_label', '')}, {line.get('size', '')}) {_money(int(line.get('line_cents') or 0))}"
        )
    return "\n".join(rows)


def notify_new_order(order: dict, env: dict | None = None) -> None:
    customer = order["customer"]
    order_id = order["id"]
    alert = (
        f"New order {order_id} ({order['mode']}).\n"
        f"{customer['name']} <{customer['email']}>\n"
        f"{customer.get('line1', '')}, {customer.get('suburb', '')} {customer.get('state', '')} {customer.get('postcode', '')}\n"
        f"Total {_money(int(order['total_cents']))} (GST included).\n\n"
        f"{_lines(order)}\n"
    )
    send_email(alert_email(env), f"New Rogers Inc Designs order {order_id}", alert, env)
    if order.get("mode") == "payid":
        body = (
            f"Hello {customer['name']},\n\n"
            f"We received order {order_id}.\n\n"
            f"Pay {_money(int(order['total_cents']))} by PayID.\n"
            f"PayID: {order.get('payid')}\n"
            f"Name: {order.get('payid_name') or 'Rogers Inc Designs'}\n"
            f"Reference: {order_id}\n\n"
            "The tee is held until the payment clears, then we send it to print. "
            "Free shipping in Australia. GST is included in the price.\n"
        )
    elif order.get("mode") == "stripe":
        postage = ""
        if order.get("shipping_cents"):
            postage = f"Postage {_money(int(order['shipping_cents']))}. "
        body = (
            f"Hello {customer['name']},\n\n"
            f"We received order {order_id}. Total {_money(int(order['total_cents']))} AUD. {postage}\n"
            "Pay by card on the secure page. The tee is not sent to print until the payment clears.\n"
        )
    elif order.get("mode") == "demo":
        body = (
            f"Hello {customer['name']},\n\n"
            f"Order {order_id} was placed in demo mode. No payment was taken and nothing will be printed.\n"
        )
    else:
        body = (
            f"Hello {customer['name']},\n\n"
            f"We received order {order_id}. Total {_money(int(order['total_cents']))}.\n"
        )
    send_email(
        customer["email"],
        f"We received your Rogers Inc Designs order {order_id}",
        body,
        env,
    )


def notify_shipped(order: dict, env: dict | None = None) -> None:
    customer = order["customer"]
    order_id = order["id"]
    body = (
        f"Hello {customer['name']},\n\n"
        f"Order {order_id} has shipped.\n"
        f"Carrier: {order.get('tracking_carrier') or ''}\n"
        f"Tracking: {order.get('tracking_number') or ''}\n"
        f"{order.get('tracking_url') or ''}\n"
    )
    send_email(
        customer["email"],
        f"Your Rogers Inc Designs order {order_id} has shipped",
        body,
        env,
    )
