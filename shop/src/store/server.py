"""Stdlib server for the Rogers Inc Designs shop."""

from __future__ import annotations

import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from store.admin import (
    COOKIE,
    admin_password,
    admin_token,
    cookie_is_valid,
    login_page,
    mark_paid_from_admin,
    orders_page,
    password_matches,
)
from store.catalog import PUBLIC_PATH, ShopError, public_catalog, quote_lines
from store.checkout import (
    buyer_view,
    checkout_public,
    confirm_stripe,
    handle_stripe_webhook,
    load_order,
    place_order,
    verify_stripe_signature,
)
from store.printful import record_package_shipped

ORDERS_PATH = PUBLIC_PATH.parent / "orders"


def _orders_dir() -> Path:
    """Order JSON lives on a Railway volume when SHOP_ORDERS_DIR is set.

    SHOP_ORDERS remains the local override used by the tests.
    """
    override = (os.environ.get("SHOP_ORDERS_DIR") or os.environ.get("SHOP_ORDERS") or "").strip()
    return Path(override) if override else ORDERS_PATH


def bind_address() -> tuple[str, int]:
    """Bind every interface on Railway's PORT.

    SHOP_PORT is the local fallback when PORT is unset. SHOP_HOST can narrow
    the interface; the default is 0.0.0.0.
    """
    host = (os.environ.get("SHOP_HOST") or "0.0.0.0").strip() or "0.0.0.0"
    raw = (os.environ.get("PORT") or os.environ.get("SHOP_PORT") or "8765").strip()
    return host, int(raw)


class ShopServer(ThreadingHTTPServer):
    def __init__(self, address, handler, orders_dir: Path):
        super().__init__(address, handler)
        self.orders_dir = orders_dir


class Handler(BaseHTTPRequestHandler):
    server: ShopServer

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            path = unquote(parsed.path)
            if path == "/api/catalog":
                self._send_json(public_catalog(checkout_public()))
                return
            if path == "/api/config":
                self._send_json(checkout_public())
                return
            if path == "/admin" or path == "/admin/":
                self._send_admin_page()
                return
            if path == "/admin/logout":
                self._send_html_page(login_page(), extra=[("Set-Cookie", _expired_cookie())])
                return
            if path.startswith("/api/orders/"):
                order_id = path.removeprefix("/api/orders/").upper()
                query = parse_qs(parsed.query)
                session_id = (query.get("session_id") or [""])[0]
                secret = os.environ.get("STRIPE_SECRET_KEY", "").strip()
                if session_id and secret:
                    view = confirm_stripe(self.server.orders_dir, order_id, session_id, secret)
                else:
                    view = buyer_view(load_order(self.server.orders_dir, order_id))
                self._send_json(view)
                return
            self._send_file(path)
        except ShopError as exc:
            self._send_json({"error": str(exc)}, exc.status)
        except Exception:
            self._send_json({"error": "The shop hit an unexpected error."}, 500)

    def do_POST(self) -> None:
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/admin/login":
                self._admin_login()
                return
            if parsed.path.startswith("/admin/orders/") and parsed.path.endswith("/paid"):
                self._admin_mark_paid(parsed.path)
                return
            if parsed.path == "/api/printful/webhook":
                record_package_shipped(self.server.orders_dir, self._read_json())
                self._send_json({"ok": True})
                return
            if parsed.path == "/api/stripe/webhook":
                self._stripe_webhook()
                return
            payload = self._read_json()
            if parsed.path == "/api/quote":
                self._send_json(quote_lines(payload.get("lines"), payload.get("customer")))
                return
            if parsed.path == "/api/checkout":
                host = self.headers.get("Host", "127.0.0.1")
                base = os.environ.get("SHOP_BASE_URL", f"http://{host}").rstrip("/")
                view = place_order(
                    self.server.orders_dir,
                    payload.get("lines"),
                    payload.get("customer"),
                    base_url=base,
                    payment=payload.get("payment"),
                )
                self._send_json(view)
                return
            self._send_json({"error": "Unknown request."}, 404)
        except ShopError as exc:
            self._send_json({"error": str(exc)}, exc.status)
        except Exception:
            self._send_json({"error": "The shop hit an unexpected error."}, 500)

    def _stripe_webhook(self) -> None:
        raw = self._read_body()
        secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
        if not secret:
            self._send_json({"error": "Stripe webhook secret is not set."}, 503)
            return
        if not verify_stripe_signature(raw, self.headers.get("Stripe-Signature", ""), secret):
            self._send_json({"error": "Bad Stripe signature."}, 400)
            return
        try:
            event = json.loads(raw.decode() or "{}")
        except json.JSONDecodeError as exc:
            raise ShopError("That request is not valid JSON.") from exc
        if not isinstance(event, dict):
            raise ShopError("That request is not valid JSON.")
        self._send_json(handle_stripe_webhook(self.server.orders_dir, event))

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length < 0 or length > 100_000:
            raise ShopError("That request is too large.")
        return self.rfile.read(length) if length else b""

    def _read_json(self) -> dict:
        raw = self._read_body() or b"{}"
        try:
            data = json.loads(raw.decode())
        except json.JSONDecodeError as exc:
            raise ShopError("That request is not valid JSON.") from exc
        if not isinstance(data, dict):
            raise ShopError("That request is not valid JSON.")
        return data

    def _read_form(self) -> dict[str, str]:
        parsed = parse_qs(self._read_body().decode(errors="replace"), keep_blank_values=True)
        return {key: values[-1] if values else "" for key, values in parsed.items()}

    def _admin_ok(self) -> bool:
        return cookie_is_valid(self.headers.get("Cookie", ""))

    def _send_admin_page(self, message: str = "") -> None:
        if not admin_password():
            self._send_html_page(login_page("Set SHOP_ADMIN_PASSWORD on the server."), status=503)
            return
        if not self._admin_ok():
            self._send_html_page(login_page(message), status=401 if message else 200)
            return
        self._send_html_page(orders_page(self.server.orders_dir, message))

    def _admin_login(self) -> None:
        if not admin_password():
            self._send_html_page(login_page("Set SHOP_ADMIN_PASSWORD on the server."), status=503)
            return
        form = self._read_form()
        if not password_matches(form.get("password", "")):
            self._send_html_page(login_page("That password is not right."), status=401)
            return
        token = admin_token(admin_password())
        self._send_html_page(
            orders_page(self.server.orders_dir),
            extra=[("Set-Cookie", f"{COOKIE}={token}; HttpOnly; Path=/admin; SameSite=Lax")],
        )

    def _admin_mark_paid(self, path: str) -> None:
        if self.headers.get("Content-Length"):
            self._read_body()
        if not self._admin_ok():
            self._send_html_page(login_page("Enter the admin password."), status=401)
            return
        order_id = path.removeprefix("/admin/orders/").removesuffix("/paid").upper()
        message = mark_paid_from_admin(self.server.orders_dir, order_id)
        self._send_html_page(orders_page(self.server.orders_dir, message))

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: str) -> None:
        relative = path.lstrip("/") or "index.html"
        candidate = (PUBLIC_PATH / relative).resolve()
        try:
            candidate.relative_to(PUBLIC_PATH.resolve())
        except ValueError:
            self._send_html(PUBLIC_PATH / "index.html")
            return
        if candidate.is_file():
            self._send_html(candidate) if candidate.suffix == ".html" else self._send_static(candidate)
            return
        self._send_html(PUBLIC_PATH / "index.html")

    def _send_static(self, path: Path) -> None:
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, path: Path) -> None:
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html_page(
        self,
        html: str,
        status: int = 200,
        extra: list[tuple[str, str]] | None = None,
    ) -> None:
        body = html.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for key, value in extra or []:
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)


def make_server(port: int = 8765, host: str = "127.0.0.1", orders_dir: Path | None = None) -> ShopServer:
    directory = orders_dir or _orders_dir()
    return ShopServer((host, port), Handler, directory)


def _expired_cookie() -> str:
    return f"{COOKIE}=; HttpOnly; Path=/admin; Max-Age=0; SameSite=Lax"


def main() -> None:
    host, port = bind_address()
    server = make_server(port, host)
    mode = checkout_public()["mode"]
    print(f"Rogers Inc Designs on http://{host}:{port} ({mode})")
    server.serve_forever()
