"""Locked prices and Marketing copy for the Rogers Inc Designs shop."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "catalog.json"
COPY_PATH = ROOT / "web-copy.json"
PUBLIC_PATH = ROOT / "public"

# Polyester AU$69 (2XL AU$73). Cotton AU$75 (2XL AU$79). Do not drift.
LOCKED_PRICES = {
    "poly": (6900, 7300),
    "cotton": (7500, 7900),
}

STATES = ("NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT")


class ShopError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_catalog() -> dict:
    data = load_json(CATALOG_PATH)
    for fabric_id, locked in LOCKED_PRICES.items():
        fabric = data["fabrics"][fabric_id]
        got = (fabric["price_cents"], fabric["price_2xl_cents"])
        if got != locked:
            raise ShopError(f"Locked price mismatch for {fabric_id}.", 500)
    products = data.get("products") or data.get("designs") or []
    data["products"] = products
    slugs = [item["slug"] for item in products]
    if len(slugs) != len(set(slugs)):
        raise ShopError("Duplicate product slug.", 500)
    if "collections" not in data:
        raise ShopError("Catalog is missing collections.", 500)
    return data


def load_copy() -> dict:
    return load_json(COPY_PATH)


def blurb(template: str, scene: str, fabric_phrase: str) -> str:
    return template.format(scene=scene.rstrip("."), fabric=fabric_phrase)


def product_fabrics(catalog: dict, product: dict) -> list[str]:
    listed = product.get("fabrics")
    if listed:
        return list(listed)
    return [fabric_id for fabric_id in ("poly", "cotton") if fabric_id in catalog["fabrics"]]


def fabric_price(catalog: dict, product: dict, fabric_id: str) -> tuple[int, int]:
    override = (product.get("prices") or {}).get(fabric_id) or {}
    shared = catalog["fabrics"][fabric_id]
    base = override.get("price_cents", shared["price_cents"])
    premium = override.get("price_2xl_cents", shared["price_2xl_cents"])
    return base, premium


def public_product(catalog: dict, copy: dict, product: dict) -> dict:
    slug = product["slug"]
    template = copy["blurb_template"]
    scene = product.get("scene", "")
    fabrics = []
    for fabric_id in product_fabrics(catalog, product):
        fabric = catalog["fabrics"][fabric_id]
        base, premium = fabric_price(catalog, product, fabric_id)
        fabrics.append(
            {
                "id": fabric_id,
                "label": fabric["label"],
                "phrase": fabric["phrase"],
                "price_cents": base,
                "price_2xl_cents": premium,
                "etsy_url": product.get("etsy", {}).get(fabric_id),
                "mockup": mockup_url(slug, fabric_id),
            }
        )
    blurbs = {item["id"]: blurb(template, scene, item["phrase"]) for item in fabrics}
    image = next((item["mockup"] for item in fabrics if item["mockup"]), None) or image_url(slug)
    return {
        "slug": slug,
        "name": product["name"],
        "listing_name": product["listing_name"],
        "collection": product.get("collection"),
        "series": product.get("series"),
        "series_name": product.get("series_name") or product.get("series") or "",
        "tags": product.get("tags") or [],
        "status": product.get("status", "live"),
        "hook": product.get("hook", ""),
        "blurbs": blurbs,
        "fabrics": fabrics,
        "image": image,
    }


def mockup_url(slug: str, fabric_id: str) -> str | None:
    for filename in (f"{slug}-aop-{fabric_id}.jpg", f"{slug}-{fabric_id}.jpg"):
        if (PUBLIC_PATH / "mockups" / filename).is_file():
            return f"/mockups/{filename}"
    return None


def image_url(slug: str) -> str | None:
    for suffix in (".jpg", ".jpeg", ".webp", ".png"):
        if (PUBLIC_PATH / "art" / f"{slug}{suffix}").is_file():
            return f"/art/{slug}{suffix}"
    return None


def public_catalog(checkout: dict) -> dict:
    catalog = load_catalog()
    copy = load_copy()
    buyer_copy = {key: value for key, value in copy.items() if key != "_meta"}
    return {
        "currency": catalog["currency"],
        "sizes": catalog["sizes"],
        "premium_sizes": catalog["premium_sizes"],
        "seo": buyer_copy["seo"],
        "home": buyer_copy["home"],
        "about": buyer_copy["about"],
        "shop": buyer_copy["shop"],
        "collections": public_collections(catalog),
        "series": public_series(catalog),
        "size_note": buyer_copy["size_note"],
        "size_chart_gap": buyer_copy["size_chart_gap"],
        "shipping": buyer_copy["shipping"],
        "delivery": buyer_copy["delivery"],
        "returns": buyer_copy["returns"],
        "returns_contact_gap": buyer_copy["returns_contact_gap"],
        "footer": buyer_copy["footer"],
        "etsy_link_label": buyer_copy["etsy_link_label"],
        "etsy_listing_url": buyer_copy["etsy_listing_url"],
        "checkout": checkout,
        "products": [
            public_product(catalog, copy, item)
            for item in catalog["products"]
            if item.get("status", "live") == "live"
        ],
    }


def public_collections(catalog: dict) -> list[dict]:
    counts: dict[str, int] = {}
    for product in catalog["products"]:
        if product.get("status", "live") != "live":
            continue
        collection_id = product.get("collection")
        counts[collection_id] = counts.get(collection_id, 0) + 1
    rows = []
    for item in catalog["collections"]:
        rows.append(
            {
                "id": item["id"],
                "name": item["name"],
                "label": item.get("label") or item["name"],
                "status": item.get("status", "live"),
                "intro": item.get("intro", ""),
                "detail": item.get("detail", ""),
                "example": item.get("example", ""),
                "count": counts.get(item["id"], 0),
            }
        )
    return rows


def public_series(catalog: dict) -> list[dict]:
    labels = {item["id"]: item.get("label") or item["id"] for item in catalog.get("series", [])}
    collections = {item["id"]: item.get("collection") for item in catalog.get("series", [])}
    seen = []
    rows = []
    for product in catalog["products"]:
        if product.get("status", "live") != "live":
            continue
        series_id = product.get("series")
        if not series_id or series_id in seen:
            continue
        seen.append(series_id)
        rows.append(
            {
                "id": series_id,
                "label": labels.get(series_id) or product.get("series_name") or series_id,
                "collection": product.get("collection") or collections.get(series_id),
            }
        )
    return rows


def find_product(catalog: dict, slug: str) -> dict:
    for product in catalog["products"]:
        if product["slug"] == slug and product.get("status", "live") == "live":
            return product
    raise ShopError("That design is not in the shop.")


def price_line(catalog: dict, slug: str, fabric: str, size: str, qty: int) -> dict:
    product = find_product(catalog, slug)
    if fabric not in product_fabrics(catalog, product):
        raise ShopError("Choose a fabric for this tee.")
    if size not in catalog["sizes"]:
        raise ShopError("Choose a size from XS to 2XL.")
    if isinstance(qty, bool) or not isinstance(qty, int) or qty < 1 or qty > 4:
        raise ShopError("Quantity is limited to 4 of each tee.")
    fabric_row = catalog["fabrics"][fabric]
    base, premium = fabric_price(catalog, product, fabric)
    unit = premium if size in catalog["premium_sizes"] else base
    template = product.get("templates", {}).get(fabric)
    return {
        "slug": slug,
        "name": product["name"],
        "listing_name": product["listing_name"],
        "series_name": product.get("series_name") or "",
        "fabric": fabric,
        "fabric_label": fabric_row["label"],
        "size": size,
        "qty": qty,
        "unit_cents": unit,
        "line_cents": unit * qty,
        "printful_product_id": fabric_row["printful_product_id"],
        "template_id": template,
    }


def public_line(line: dict) -> dict:
    hidden = {"printful_product_id", "template_id"}
    return {key: value for key, value in line.items() if key not in hidden}


def quote_lines(raw_lines: list) -> dict:
    if not isinstance(raw_lines, list):
        raise ShopError("Cart lines are missing.")
    if len(raw_lines) > 12:
        raise ShopError("Too many lines in this order.")
    catalog = load_catalog()
    priced = []
    for raw in raw_lines:
        if not isinstance(raw, dict):
            raise ShopError("A cart line is unreadable.")
        priced.append(
            price_line(
                catalog,
                str(raw.get("slug", "")),
                str(raw.get("fabric", "")),
                str(raw.get("size", "")),
                raw.get("qty"),
            )
        )
    total = sum(line["line_cents"] for line in priced)
    return {
        "lines": [public_line(line) for line in priced],
        "shipping_cents": 0,
        "total_cents": total,
        "currency": "AUD",
        "gst_included": True,
    }


def _clean(value: object, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    text = " ".join(value.split())
    return text[:limit]


def validate_customer(raw: object) -> dict:
    if not isinstance(raw, dict):
        raise ShopError("Add a name and an Australian address.")
    name = _clean(raw.get("name"), 80)
    email = _clean(raw.get("email"), 120)
    phone = _clean(raw.get("phone"), 30)
    line1 = _clean(raw.get("line1"), 120)
    line2 = _clean(raw.get("line2"), 120)
    suburb = _clean(raw.get("suburb"), 60)
    state = _clean(raw.get("state"), 8).upper()
    postcode = _clean(raw.get("postcode"), 8)
    if len(name) < 2:
        raise ShopError("Enter the name for the parcel.")
    if "@" not in email or "." not in email.split("@")[-1] or " " in email:
        raise ShopError("Enter an email address.")
    if phone:
        digits = "".join(ch for ch in phone if ch.isdigit())
        if len(digits) < 8:
            raise ShopError("Enter a phone number, or leave it blank.")
    if len(line1) < 4:
        raise ShopError("Enter a street address.")
    if len(suburb) < 2:
        raise ShopError("Enter a suburb.")
    if state not in STATES:
        raise ShopError("Choose an Australian state or territory.")
    if len(postcode) != 4 or not postcode.isdigit():
        raise ShopError("Enter a 4-digit postcode.")
    return {
        "name": name,
        "email": email,
        "phone": phone,
        "line1": line1,
        "line2": line2,
        "suburb": suburb,
        "state": state,
        "postcode": postcode,
        "country": "AU",
    }
