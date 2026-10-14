"""Order mail. Missing SMTP settings are logged and skipped."""

from __future__ import annotations

import json
import logging
import os
import smtplib
import ssl
import threading
import urllib.error
import urllib.request
from email.message import EmailMessage

log = logging.getLogger("store")

DEFAULT_ALERT = "rogersinc426@gmail.com"
SENDER_NAME = "Rogers Inc Designs"
BREVO_URL = "https://api.brevo.com/v3/smtp/email"
SMTP_TIMEOUT = 8
_pending: list[threading.Thread] = []
_pending_lock = threading.Lock()


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


def sender_email(env: dict | None = None) -> str:
    """Verified From address. SMTP_FROM wins, then SHOP_FROM_EMAIL, then the Gmail sender."""
    env = os.environ if env is None else env
    return (
        (env.get("SMTP_FROM") or "").strip()
        or (env.get("SHOP_FROM_EMAIL") or "").strip()
        or DEFAULT_ALERT
    )


def _reference(reference: str) -> str:
    return reference or "-"


def send_brevo(to: str, subject: str, body: str, env: dict) -> None:
    key = (env.get("BREVO_API_KEY") or "").strip()
    payload = {
        "sender": {"name": SENDER_NAME, "email": sender_email(env)},
        "to": [{"email": to}],
        "subject": subject,
        "textContent": body,
    }
    request = urllib.request.Request(
        BREVO_URL,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={
            "api-key": key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=SMTP_TIMEOUT) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:300]
        raise RuntimeError(f"Brevo HTTP {exc.code}: {detail}") from exc


def _send_smtp(to: str, subject: str, body: str, env: dict) -> bool:
    cfg = smtp_config(env)
    if cfg is None:
        return False
    message = EmailMessage()
    message["From"] = cfg["sender"]
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    if cfg["port"] == 465:
        with smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=SMTP_TIMEOUT) as smtp:
            if cfg["user"]:
                smtp.login(cfg["user"], cfg["password"])
            smtp.send_message(message)
    else:
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=SMTP_TIMEOUT) as smtp:
            smtp.ehlo()
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
            if cfg["user"]:
                smtp.login(cfg["user"], cfg["password"])
            smtp.send_message(message)
    return True


def send_email(
    to: str,
    subject: str,
    body: str,
    env: dict | None = None,
    reference: str = "",
) -> bool:
    env = os.environ if env is None else env
    order_ref = _reference(reference)
    if not to:
        log.warning("email skipped order=%s: no recipient", order_ref)
        return False
    if (env.get("BREVO_API_KEY") or "").strip():
        log.warning("email attempt order=%s to=%s via=brevo", order_ref, to)
        try:
            send_brevo(to, subject, body, env)
        except Exception as exc:
            log.warning("email failed order=%s to=%s via=brevo: %s", order_ref, to, exc)
        else:
            log.warning("email sent order=%s to=%s via=brevo", order_ref, to)
            return True
    log.warning("email attempt order=%s to=%s via=smtp", order_ref, to)
    try:
        if _send_smtp(to, subject, body, env):
            log.warning("email sent order=%s to=%s via=smtp", order_ref, to)
            return True
    except Exception as exc:
        log.warning("email failed order=%s to=%s via=smtp: %s", order_ref, to, exc)
        return False
    log.warning("email skipped order=%s to=%s: no Brevo key and SMTP is not set", order_ref, to)
    return False


def _lines(order: dict) -> str:
    rows = []
    for line in order.get("lines") or []:
        rows.append(
            f"- {line.get('qty', 1)} × {line.get('listing_name') or line.get('name')} "
            f"({line.get('fabric_label', '')}, {line.get('size', '')}) {_money(int(line.get('line_cents') or 0))}"
        )
    return "\n".join(rows)


def _snapshot(env: dict | None) -> dict:
    source = os.environ if env is None else env
    return {key: value for key, value in source.items()}


def _start(name: str, target) -> None:
    thread = threading.Thread(target=target, name=name, daemon=True)
    with _pending_lock:
        _pending.append(thread)
    thread.start()


def wait_for_mail(timeout: float = 2.0) -> None:
    """Join mail started during a test. The shop request itself does not wait."""
    with _pending_lock:
        pending = list(_pending)
        _pending.clear()
    for thread in pending:
        thread.join(timeout)


def notify_new_order_later(order: dict, env: dict | None = None) -> None:
    snapshot = _snapshot(env)
    payload = json.loads(json.dumps(order))

    def run() -> None:
        try:
            notify_new_order(payload, snapshot)
        except Exception as exc:
            log.warning("order email failed: %s", exc)

    _start("shop-order-email", run)


def notify_shipped_later(order: dict, env: dict | None = None) -> None:
    snapshot = _snapshot(env)
    payload = json.loads(json.dumps(order))

    def run() -> None:
        try:
            notify_shipped(payload, snapshot)
        except Exception as exc:
            log.warning("shipped email failed: %s", exc)

    _start("shop-shipped-email", run)


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
    send_email(alert_email(env), f"New Rogers Inc Designs order {order_id}", alert, env, reference=order_id)
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
        reference=order_id,
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
        reference=order_id,
    )
