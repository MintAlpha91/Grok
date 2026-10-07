"""Locked prices and Marketing copy for the Rogers Inc Designs shop."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "catalog.json"
COPY_PATH = ROOT / "web-copy.json"
PUBLIC_PATH = ROOT / "public"

# Official-store prices, GST-inclusive. Etsy stays higher. Do not list Etsy amounts here.
# Poly AU$65 (2XL +AU$4). Cotton AU$71 (2XL +AU$4), after first sales.
# Chest DTG AU$47 (2XL +AU$4, 3XL +AU$7). No 4XL or 5XL in v1.
LOCKED_PRICES = {
    "poly": {"price_cents": 6500, "premiums_cents": {"2XL": 400}, "price_2xl_cents": 6900},
    "cotton": {"price_cents": 7100, "premiums_cents": {"2XL": 400}, "price_2xl_cents": 7500},
    "chest": {"price_cents": 4700, "premiums_cents": {"2XL": 400, "3XL": 700}},
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
        if fabric["price_cents"] != locked["price_cents"]:
            raise ShopError(f"Locked price mismatch for {fabric_id}.", 500)
        if fabric.get("premiums_cents") != locked["premiums_cents"]:
            raise ShopError(f"Locked size premium mismatch for {fabric_id}.", 500)
        if "price_2xl_cents" in locked and fabric.get("price_2xl_cents") != locked["price_2xl_cents"]:
            raise ShopError(f"Locked 2XL price mismatch for {fabric_id}.", 500)
        etsy = (data.get("pricing") or {}).get("etsy_cents") or {}
        if etsy.get(fabric_id) == fabric["price_cents"]:
            raise ShopError(f"Etsy price is listed on the site for {fabric_id}.", 500)
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
    return [
        fabric_id
        for fabric_id, row in catalog["fabrics"].items()
        if row.get("kind", "aop") == "aop"
    ]


def fabric_is_orderable(fabric: dict) -> bool:
    return fabric.get("status", "live") == "live"


COLLECTION_FLOOR = 10
# Gothic and Fuel stay preview until Jason clears them. Never featured from stored live.
OFF_FEATURED_COLLECTIONS = {"gothic-blackletter", "fuel"}


def shop_visible(product: dict) -> bool:
    """Live tees, plus preview cards that can be ordered in the demo shop."""
    return product.get("status", "live") in {"live", "preview"}


def catalog_listed(product: dict) -> bool:
    """Shop cards, including one upcoming design that cannot be ordered."""
    if shop_visible(product):
        return True
    return product.get("status") == "upcoming" and product.get("surface") == "single"


def presented_collection_status(
    status: str,
    count: int,
    collection_id: str = "",
    floor: int = COLLECTION_FLOOR,
) -> str:
    """A thin lane is not the public storefront. Fuel and gothic stay off featured."""
    if collection_id in OFF_FEATURED_COLLECTIONS and count < floor and status != "hidden":
        return "upcoming" if collection_id == "fuel" else "preview"
    if collection_id in OFF_FEATURED_COLLECTIONS and status == "live":
        return "preview"
    if status == "live" and count < floor:
        return "ready"
    return status


def presented_product_status(product: dict) -> str:
    """Short series and off-featured lanes are preview cards, not the featured list."""
    status = product.get("status", "live")
    if status == "live" and product.get("collection") in OFF_FEATURED_COLLECTIONS:
        return "preview"
    return status


def fabric_price(catalog: dict, product: dict, fabric_id: str) -> tuple[int, int]:
    override = (product.get("prices") or {}).get(fabric_id) or {}
    shared = catalog["fabrics"][fabric_id]
    base = override.get("price_cents", shared["price_cents"])
    premiums = shared.get("premiums_cents") or {}
    premium = override.get("price_2xl_cents", shared.get("price_2xl_cents", base + premiums.get("2XL", 0)))
    return base, premium


def unit_cents(catalog: dict, product: dict, fabric_id: str, size: str) -> int:
    fabric = catalog["fabrics"][fabric_id]
    base, legacy_premium = fabric_price(catalog, product, fabric_id)
    premiums = (product.get("prices") or {}).get(fabric_id, {}).get("premiums_cents")
    if premiums is None:
        premiums = fabric.get("premiums_cents") or {}
    if premiums:
        return base + int(premiums.get(size, 0))
    if size in catalog.get("premium_sizes", []):
        return legacy_premium
    return base


def gst_included_cents(total_cents: int) -> int:
    """GST already inside an inclusive price. One eleventh, nearest cent. Not added on top."""
    return (total_cents + 5) // 11


def settle(lines: list[dict], country: str = "AU") -> dict:
    if country != "AU":
        raise ShopError(
            "Overseas postage is charged and is not open yet. This shop does not cover international shipping."
        )
    goods = sum(line["line_cents"] for line in lines)
    shipping = 0
    total = goods + shipping
    return {
        "shipping_cents": shipping,
        "goods_cents": goods,
        "gst_cents": gst_included_cents(total),
        "gst_included": True,
        "total_cents": total,
        "currency": "AUD",
    }


def public_product(catalog: dict, copy: dict, product: dict) -> dict:
    slug = product["slug"]
    scene = product.get("scene", "")
    fabrics = []
    held = []
    blurbs = {}
    for fabric_id in product_fabrics(catalog, product):
        fabric = catalog["fabrics"][fabric_id]
        base, premium = fabric_price(catalog, product, fabric_id)
        template_key = "blurb_template_dtg" if fabric.get("kind") == "dtg" else "blurb_template"
        template = copy.get(template_key) or copy["blurb_template"]
        row = {
            "id": fabric_id,
            "label": fabric["label"],
            "phrase": fabric["phrase"],
            "status": fabric.get("status", "live"),
            "price_cents": base,
            "price_2xl_cents": premium,
            "sizes": fabric.get("sizes") or catalog["sizes"],
            "premiums_cents": fabric.get("premiums_cents") or {},
            "etsy_url": product.get("etsy", {}).get(fabric_id),
            "mockup": mockup_url(slug, fabric_id, product),
        }
        if fabric.get("size_note"):
            row["size_note"] = fabric["size_note"]
        blurbs[fabric_id] = blurb(template, scene, fabric["phrase"])
        if fabric_is_orderable(fabric):
            fabrics.append(row)
        else:
            held.append(row)
    image = next((item["mockup"] for item in fabrics if item["mockup"]), None) or image_url(slug)
    gallery = []
    for name in product.get("gallery") or []:
        if (PUBLIC_PATH / "mockups" / name).is_file():
            url = f"/mockups/{name}"
            if url not in gallery:
                gallery.append(url)
    if image and image not in gallery:
        gallery.insert(0, image)
    return {
        "slug": slug,
        "name": product["name"],
        "listing_name": product["listing_name"],
        "collection": product.get("collection"),
        "series": product.get("series"),
        "series_name": product.get("series_name") or product.get("series") or "",
        "tags": product.get("tags") or [],
        "status": presented_product_status(product),
        "hook": product.get("hook", ""),
        "blurbs": blurbs,
        "fabrics": fabrics,
        "held_fabrics": held,
        "image": image,
        "gallery": gallery,
    }


def mockup_url(slug: str, fabric_id: str, product: dict | None = None) -> str | None:
    named = ((product or {}).get("mockups") or {}).get(fabric_id)
    filenames = [named] if named else []
    filenames.extend((f"{slug}-aop-{fabric_id}.jpg", f"{slug}-{fabric_id}.jpg"))
    for filename in filenames:
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
        "offer": data_offer(catalog),
        "addons": public_addons(catalog),
        "fabrics": public_fabrics(catalog),
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
            if catalog_listed(item)
        ],
    }


def data_offer(catalog: dict) -> dict:
    offer = catalog.get("offer") or {}
    return {
        "story": (catalog.get("pricing") or {}).get("story", "official-store"),
        "hero_fabric": offer.get("hero_fabric", "poly"),
        "hero_line": offer.get("hero_line", ""),
        "story_line": offer.get("story_line") or offer.get("parity_line") or "",
    }


def public_addons(catalog: dict) -> list[dict]:
    rows = []
    for item in catalog.get("addons") or []:
        rows.append(
            {
                "id": item["id"],
                "name": item["name"],
                "status": item.get("status", "held"),
                "with_shirt_cents": item["with_shirt_cents"],
                "line": item.get("line", ""),
                "note": item.get("note", ""),
            }
        )
    return rows


def public_fabrics(catalog: dict) -> list[dict]:
    rows = []
    for fabric_id, fabric in catalog["fabrics"].items():
        rows.append(
            {
                "id": fabric_id,
                "label": fabric["label"],
                "kind": fabric.get("kind", ""),
                "role": fabric.get("role", ""),
                "status": fabric.get("status", "live"),
                "price_cents": fabric["price_cents"],
                "sizes": fabric.get("sizes") or catalog["sizes"],
                "premiums_cents": fabric.get("premiums_cents") or {},
                "omit_sizes": fabric.get("omit_sizes") or [],
            }
        )
    return rows


def public_collections(catalog: dict) -> list[dict]:
    counts: dict[str, int] = {}
    for product in catalog["products"]:
        if not catalog_listed(product):
            continue
        collection_id = product.get("collection")
        counts[collection_id] = counts.get(collection_id, 0) + 1
    rows = []
    for item in catalog["collections"]:
        if item.get("status") == "hidden":
            continue
        count = counts.get(item["id"], 0)
        status = presented_collection_status(item.get("status", "live"), count, item["id"])
        rows.append(
            {
                "id": item["id"],
                "name": item["name"],
                "label": item.get("label") or item["name"],
                "status": status,
                "sub": item.get("sub", ""),
                "intro": item.get("intro", ""),
                "detail": item.get("detail", ""),
                "example": item.get("example", ""),
                "landing": item.get("landing") or item["id"],
                "fabric": item.get("fabric") or "",
                "count": count,
            }
        )
    return rows


def public_series(catalog: dict) -> list[dict]:
    labels = {item["id"]: item.get("label") or item["id"] for item in catalog.get("series", [])}
    blurbs = {item["id"]: item.get("blurb", "") for item in catalog.get("series", [])}
    collections = {item["id"]: item.get("collection") for item in catalog.get("series", [])}
    hidden = {item["id"] for item in catalog.get("collections", []) if item.get("status") == "hidden"}
    seen = []
    rows = []
    for product in catalog["products"]:
        if not catalog_listed(product):
            continue
        if product.get("collection") in hidden:
            continue
        series_id = product.get("series")
        if not series_id or series_id in seen:
            continue
        seen.append(series_id)
        rows.append(
            {
                "id": series_id,
                "label": labels.get(series_id) or product.get("series_name") or series_id,
                "blurb": blurbs.get(series_id, ""),
                "collection": product.get("collection") or collections.get(series_id),
            }
        )
    order = {item["id"]: index for index, item in enumerate(catalog.get("series", []))}
    rows.sort(key=lambda row: order.get(row["id"], 100))
    return rows


def find_product(catalog: dict, slug: str) -> dict:
    for product in catalog["products"]:
        if product["slug"] == slug and shop_visible(product):
            return product
    raise ShopError("That design is not in the shop.")


def price_line(catalog: dict, slug: str, fabric: str, size: str, qty: int) -> dict:
    product = find_product(catalog, slug)
    if fabric not in product_fabrics(catalog, product):
        raise ShopError("Choose a fabric for this tee.")
    fabric_row = catalog["fabrics"][fabric]
    if not fabric_is_orderable(fabric_row):
        raise ShopError(f"{fabric_row['label']} is not on sale yet.")
    sizes = fabric_row.get("sizes") or catalog["sizes"]
    if size not in sizes:
        raise ShopError("Choose a size from this tee's list.")
    if isinstance(qty, bool) or not isinstance(qty, int) or qty < 1 or qty > 4:
        raise ShopError("Quantity is limited to 4 of each tee.")
    unit = unit_cents(catalog, product, fabric, size)
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
        "printful_product_id": fabric_row.get("printful_product_id"),
        "template_id": template,
    }


def public_line(line: dict) -> dict:
    hidden = {"printful_product_id", "template_id"}
    return {key: value for key, value in line.items() if key not in hidden}


def price_addon(catalog: dict, addon_id: str, qty: int, parent_slug: str) -> dict:
    addon = next((item for item in catalog.get("addons") or [] if item["id"] == addon_id), None)
    if addon is None:
        raise ShopError("That add-on is not in the shop.")
    if addon.get("status") != "live":
        raise ShopError("Matching wallpapers are not on sale yet.")
    if isinstance(qty, bool) or not isinstance(qty, int) or qty < 1 or qty > 4:
        raise ShopError("Quantity is limited to 4 of each tee.")
    unit = int(addon["with_shirt_cents"])
    return {
        "slug": parent_slug,
        "name": addon["name"],
        "listing_name": addon["name"],
        "series_name": "",
        "fabric": "digital",
        "fabric_label": "Download",
        "size": "",
        "qty": qty,
        "unit_cents": unit,
        "line_cents": unit * qty,
        "addon": addon_id,
        "printful_product_id": None,
        "template_id": None,
    }


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
    settled = settle(priced)
    return {
        "lines": [public_line(line) for line in priced],
        **settled,
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
