"""Printful fulfilment. PayID is marked paid by hand, then this creates the order.

PRINTFUL_AUTO_CONFIRM=true submits the order. Otherwise Printful keeps a draft.
A missing PRINTFUL_API_KEY is logged and skipped.
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import urllib.error
import urllib.request
from pathlib import Path

from store.catalog import PUBLIC_PATH, ShopError, load_catalog
from store.checkout import ORDER_ID, _write, load_order

log = logging.getLogger("store")

PRINT_ROOT = PUBLIC_PATH.parent / "print-ready"
WHITE_SHIRT_COLLECTIONS = {"fuel", "gothic-blackletter"}


def auto_confirm(env: dict | None = None) -> bool:
    env = os.environ if env is None else env
    return (env.get("PRINTFUL_AUTO_CONFIRM") or "").strip().lower() in {"1", "true", "yes"}


def shirt_color(product: dict) -> str:
    explicit = str(product.get("shirt_color") or "").strip().lower()
    if explicit:
        return explicit
    if product.get("collection") in WHITE_SHIRT_COLLECTIONS:
        return "white"
    return "black"


def variant_id(catalog: dict, product: dict, fabric_id: str, size: str) -> int:
    fabric = catalog["fabrics"].get(fabric_id) or {}
    variants = fabric.get("printful_variants") or {}
    if not variants:
        raise ShopError(f"No Printful size map for {fabric_id}.", 409)
    sample = next(iter(variants.values()))
    if isinstance(sample, dict):
        color = shirt_color(product)
        row = variants.get(color)
        if not isinstance(row, dict):
            raise ShopError(f"No Printful {color} shirt for {product['slug']}.", 409)
        variant = row.get(size)
    else:
        variant = variants.get(size)
    if not isinstance(variant, int):
        raise ShopError(f"No Printful variant for {product['slug']} {fabric_id} {size}.", 409)
    return variant


def placement_for(catalog: dict, fabric_id: str) -> str:
    fabric = catalog["fabrics"].get(fabric_id) or {}
    return str(fabric.get("printful_placement") or "front")


def stored_product(catalog: dict, slug: str) -> dict:
    for product in catalog["products"]:
        if product["slug"] == slug:
            return product
    raise ShopError(f"Unknown design {slug}.", 409)


def print_path(product: dict) -> Path:
    relative = str(product.get("print_ready") or "").strip()
    if not relative or relative.startswith(("/", "\\")) or ".." in Path(relative).parts:
        raise ShopError(f"No print file for {product['slug']}.", 409)
    path = (PRINT_ROOT / relative).resolve()
    try:
        path.relative_to(PRINT_ROOT.resolve())
    except ValueError as exc:
        raise ShopError(f"No print file for {product['slug']}.", 409) from exc
    if not path.is_file():
        raise ShopError(f"Print file is missing for {product['slug']}.", 409)
    return path


def read_print_bytes(path: Path) -> bytes:
    return path.read_bytes()


def _api_key(env: dict) -> str:
    return (env.get("PRINTFUL_API_KEY") or "").strip()


def _headers(env: dict, content_type: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {_api_key(env)}", "User-Agent": "RogersIncDesignsShop"}
    store_id = (env.get("PRINTFUL_STORE_ID") or "").strip()
    if store_id:
        headers["X-PF-Store-Id"] = store_id
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def _multipart(filename: str, content: bytes) -> tuple[bytes, str]:
    boundary = "----RogersShop" + secrets.token_hex(8)
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode(),
            b"Content-Type: image/png\r\n\r\n",
            content,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    return body, f"multipart/form-data; boundary={boundary}"


def printful_request(
    env: dict,
    method: str,
    path: str,
    payload: dict | None = None,
    file: tuple[str, bytes] | None = None,
) -> dict:
    """Call the Printful API. Tests patch this. No live key is used here."""
    if file is not None:
        data, content_type = _multipart(file[0], file[1])
    elif payload is not None:
        data = json.dumps(payload).encode()
        content_type = "application/json"
    else:
        data = None
        content_type = None
    request = urllib.request.Request(
        "https://api.printful.com" + path,
        data=data,
        method=method,
        headers=_headers(env, content_type),
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            parsed = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        message = "Printful refused the order."
        try:
            message = json.loads(detail)["error"]["message"]
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
        raise ShopError(message, 502) from exc
    except urllib.error.URLError as exc:
        raise ShopError("Printful could not be reached.", 502) from exc
    if not isinstance(parsed, dict):
        raise ShopError("Printful returned an unreadable response.", 502)
    result = parsed.get("result", parsed)
    if not isinstance(result, dict):
        raise ShopError("Printful returned an unreadable response.", 502)
    return result


def _dollars(cents: int) -> str:
    return f"{cents / 100:.2f}"


def build_items(order: dict, env: dict) -> list[dict]:
    catalog = load_catalog()
    items = []
    uploads: dict[str, int] = {}
    for line in order["lines"]:
        if line.get("addon") or line.get("fabric") in {"digital", "wallpaper"}:
            continue
        product = stored_product(catalog, line["slug"])
        path = print_path(product)
        key = str(path)
        file_id = uploads.get(key)
        if file_id is None:
            uploaded = printful_request(env, "POST", "/files", file=(path.name, read_print_bytes(path)))
            file_id = uploaded.get("id")
            if not isinstance(file_id, int):
                raise ShopError(f"Printful did not accept the print file for {line['slug']}.", 502)
            uploads[key] = file_id
        items.append(
            {
                "variant_id": variant_id(catalog, product, line["fabric"], line["size"]),
                "quantity": line["qty"],
                "name": line.get("listing_name") or line.get("name") or line["slug"],
                "retail_price": _dollars(line["unit_cents"]),
                "files": [{"id": file_id, "type": placement_for(catalog, line["fabric"])}],
            }
        )
    return items


def order_payload(order: dict, items: list[dict]) -> dict:
    customer = order["customer"]
    recipient = {
        "name": customer["name"],
        "address1": customer["line1"],
        "city": customer["suburb"],
        "state_code": customer["state"],
        "country_code": "AU",
        "zip": customer["postcode"],
        "email": customer["email"],
    }
    if customer.get("line2"):
        recipient["address2"] = customer["line2"]
    if customer.get("phone"):
        recipient["phone"] = customer["phone"]
    return {
        "external_id": order["id"],
        "shipping": "STANDARD",
        "recipient": recipient,
        "items": items,
    }


def submit_printful(order: dict, env: dict | None = None) -> dict | None:
    """Create the Printful order. None means the API key is unset."""
    env = os.environ if env is None else env
    if not _api_key(env):
        log.warning("printful skipped: PRINTFUL_API_KEY is not set")
        return None
    items = build_items(order, env)
    if not items:
        log.warning("printful skipped: order %s has no physical lines", order["id"])
        return {"id": None, "status": "no_physical_items", "confirmed": False}
    confirm = auto_confirm(env)
    created = printful_request(
        env,
        "POST",
        "/orders?confirm=true" if confirm else "/orders?confirm=false",
        order_payload(order, items),
    )
    printful_id = created.get("id")
    if not isinstance(printful_id, int):
        raise ShopError("Printful did not return an order id.", 502)
    return {
        "id": printful_id,
        "status": created.get("status") or ("pending" if confirm else "draft"),
        "confirmed": confirm,
    }


def mark_order_paid(orders_dir: Path, order_id: str, env: dict | None = None) -> dict:
    """Record payment, then create the Printful order once."""
    env = os.environ if env is None else env
    order = load_order(orders_dir, order_id)
    order["status"] = "paid"
    order["payment_taken"] = True
    order["fulfillment_hold"] = "paid"
    if order.get("printful_order_id"):
        _write(orders_dir, order)
        return order
    _write(orders_dir, order)
    try:
        result = submit_printful(order, env)
    except ShopError as exc:
        order["printful_error"] = str(exc)
        order["printful_status"] = "error"
        _write(orders_dir, order)
        return order
    if result is None:
        order["printful_status"] = "skipped"
        order["printful_error"] = ""
        _write(orders_dir, order)
        return order
    if result.get("id"):
        order["printful_order_id"] = result["id"]
    order["printful_status"] = result.get("status") or "draft"
    order["printful_confirmed"] = bool(result.get("confirmed"))
    order["printful_error"] = ""
    if result.get("confirmed"):
        order["print_or_ship"] = True
        order["automatic_print"] = True
    _write(orders_dir, order)
    return order


def list_orders(orders_dir: Path) -> list[dict]:
    if not orders_dir.is_dir():
        return []
    rows = []
    for path in orders_dir.glob("*.json"):
        try:
            order = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(order, dict) and ORDER_ID.match(str(order.get("id", ""))):
            rows.append(order)
    rows.sort(key=lambda item: item.get("created_brisbane") or "", reverse=True)
    return rows


def find_order_for_shipment(orders_dir: Path, payload: dict) -> dict:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    remote = data.get("order") if isinstance(data.get("order"), dict) else {}
    external = str(remote.get("external_id") or "")
    if ORDER_ID.match(external):
        return load_order(orders_dir, external)
    printful_id = remote.get("id")
    for order in list_orders(orders_dir):
        if printful_id is not None and order.get("printful_order_id") == printful_id:
            return order
    raise ShopError("Unknown order.", 404)


def record_package_shipped(orders_dir: Path, payload: dict) -> dict:
    """Store tracking from a Printful package_shipped webhook."""
    if not isinstance(payload, dict) or payload.get("type") != "package_shipped":
        return {"ignored": True}
    order = find_order_for_shipment(orders_dir, payload)
    data = payload.get("data") or {}
    shipment = data.get("shipment") if isinstance(data.get("shipment"), dict) else {}
    tracking = str(shipment.get("tracking_number") or "")
    already = order.get("status") == "shipped" and order.get("tracking_number") == tracking and tracking
    order["status"] = "shipped"
    order["print_or_ship"] = True
    order["tracking_number"] = tracking
    order["tracking_url"] = str(shipment.get("tracking_url") or "")
    order["tracking_carrier"] = str(shipment.get("carrier") or "")
    order["shipped_at"] = str(shipment.get("ship_date") or shipment.get("shipped_at") or "")
    order["fulfillment_hold"] = "shipped"
    _write(orders_dir, order)
    saved = dict(order)
    saved["_shipment_already_recorded"] = already
    return saved
