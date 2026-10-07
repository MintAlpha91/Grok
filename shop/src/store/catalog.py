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
    slugs = [item["slug"] for item in data["designs"]]
    if len(slugs) != len(set(slugs)):
        raise ShopError("Duplicate design slug.", 500)
    return data


def load_copy() -> dict:
    return load_json(COPY_PATH)


def blurb(copy: dict, slug: str, fabric_phrase: str) -> str:
    scene = copy["designs"][slug]["scene"].rstrip(".")
    return copy["blurb_template"].format(scene=scene, fabric=fabric_phrase)


def public_design(catalog: dict, copy: dict, design: dict) -> dict:
    slug = design["slug"]
    words = copy["designs"][slug]
    fabrics = []
    for fabric_id in ("poly", "cotton"):
        fabric = catalog["fabrics"][fabric_id]
        fabrics.append(
            {
                "id": fabric_id,
                "label": fabric["label"],
                "phrase": fabric["phrase"],
                "price_cents": fabric["price_cents"],
                "price_2xl_cents": fabric["price_2xl_cents"],
                "etsy_url": design.get("etsy", {}).get(fabric_id),
            }
        )
    return {
        "slug": slug,
        "name": design["name"],
        "listing_name": design["listing_name"],
        "series": design["series"],
        "series_name": design["series_name"],
        "hook": words["hook"],
        "blurbs": {
            "poly": blurb(copy, slug, "polyester"),
            "cotton": blurb(copy, slug, "cotton"),
        },
        "fabrics": fabrics,
        "image": image_url(slug),
    }


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
        "series": buyer_copy["series"],
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
        "designs": [public_design(catalog, copy, item) for item in catalog["designs"]],
    }


def find_design(catalog: dict, slug: str) -> dict:
    for design in catalog["designs"]:
        if design["slug"] == slug:
            return design
    raise ShopError("That design is not in the shop.")


def price_line(catalog: dict, slug: str, fabric: str, size: str, qty: int) -> dict:
    design = find_design(catalog, slug)
    if fabric not in catalog["fabrics"]:
        raise ShopError("Choose polyester or cotton.")
    if size not in catalog["sizes"]:
        raise ShopError("Choose a size from XS to 2XL.")
    if isinstance(qty, bool) or not isinstance(qty, int) or qty < 1 or qty > 4:
        raise ShopError("Quantity is limited to 4 of each tee.")
    fabric_row = catalog["fabrics"][fabric]
    if size in catalog["premium_sizes"]:
        unit = fabric_row["price_2xl_cents"]
    else:
        unit = fabric_row["price_cents"]
    template = design.get("templates", {}).get(fabric)
    return {
        "slug": slug,
        "name": design["name"],
        "listing_name": design["listing_name"],
        "series_name": design["series_name"],
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
