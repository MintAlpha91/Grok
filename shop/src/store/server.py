"""Stdlib server for the Rogers Inc Designs shop."""

from __future__ import annotations

import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from store.catalog import PUBLIC_PATH, ShopError, public_catalog, quote_lines
from store.checkout import (
    checkout_public,
    confirm_stripe,
    load_order,
    place_order,
    buyer_view,
)

ORDERS_PATH = PUBLIC_PATH.parent / "orders"


def _orders_dir() -> Path:
    override = os.environ.get("SHOP_ORDERS")
    return Path(override) if override else ORDERS_PATH


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
            payload = self._read_json()
            if parsed.path == "/api/quote":
                self._send_json(quote_lines(payload.get("lines")))
                return
            if parsed.path == "/api/checkout":
                host = self.headers.get("Host", "127.0.0.1")
                base = os.environ.get("SHOP_BASE_URL", f"http://{host}").rstrip("/")
                view = place_order(
                    self.server.orders_dir,
                    payload.get("lines"),
                    payload.get("customer"),
                    base_url=base,
                )
                self._send_json(view)
                return
            self._send_json({"error": "Unknown request."}, 404)
        except ShopError as exc:
            self._send_json({"error": str(exc)}, exc.status)
        except Exception:
            self._send_json({"error": "The shop hit an unexpected error."}, 500)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length < 0 or length > 100_000:
            raise ShopError("That request is too large.")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode())
        except json.JSONDecodeError as exc:
            raise ShopError("That request is not valid JSON.") from exc
        if not isinstance(data, dict):
            raise ShopError("That request is not valid JSON.")
        return data

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


def make_server(port: int = 8765, host: str = "127.0.0.1", orders_dir: Path | None = None) -> ShopServer:
    directory = orders_dir or _orders_dir()
    return ShopServer((host, port), Handler, directory)


def main() -> None:
    port = int(os.environ.get("SHOP_PORT", "8765"))
    host = os.environ.get("SHOP_HOST", "0.0.0.0")
    server = make_server(port, host)
    mode = checkout_public()["mode"]
    print(f"Rogers Inc Designs on http://127.0.0.1:{port} ({mode})")
    server.serve_forever()
