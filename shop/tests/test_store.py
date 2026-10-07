"""Prices, Marketing copy, and checkout honesty for the Rogers Inc Designs shop."""

import json
import os
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from store.catalog import (  # noqa: E402
    LOCKED_PRICES,
    ShopError,
    blurb,
    catalog_listed,
    load_catalog,
    load_copy,
    presented_collection_status,
    public_catalog,
    quote_lines,
    settle,
    unit_cents,
    validate_customer,
)
from store.checkout import (  # noqa: E402
    _form_body,
    checkout_mode,
    checkout_public,
    confirm_stripe,
    place_order,
    stripe_fields,
)
from store.server import make_server  # noqa: E402

ENV_KEYS = (
    "STRIPE_SECRET_KEY",
    "SHOP_PAYID",
    "SHOP_PAYID_NAME",
    "SHOP_CHECKOUT",
    "SHOP_ORDERS",
    "SHOP_BASE_URL",
)


def snapshot_env():
    return {key: os.environ.get(key) for key in ENV_KEYS}


def restore_env(saved):
    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def clear_payment_env():
    for key in ENV_KEYS:
        os.environ.pop(key, None)


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError(f"{path.name} is not a PNG")
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    return width, height


def jpeg_size(path: Path) -> tuple[int, int]:
    """Read width and height from a JPEG SOF marker. Tests stay on the stdlib."""
    data = path.read_bytes()
    if data[:2] != b"\xff\xd8":
        raise AssertionError(f"{path.name} is not a JPEG")
    index = 2
    while index + 9 < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        if marker in (0xC0, 0xC1, 0xC2):
            height = int.from_bytes(data[index + 5:index + 7], "big")
            width = int.from_bytes(data[index + 7:index + 9], "big")
            return width, height
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            index += 2
            continue
        length = int.from_bytes(data[index + 2:index + 4], "big")
        if length < 2:
            break
        index += 2 + length
    raise AssertionError(f"{path.name} has no SOF marker")


class CopyAndPriceTests(unittest.TestCase):
    def test_prices_stay_locked(self):
        catalog = load_catalog()
        for fabric, locked in LOCKED_PRICES.items():
            row = catalog["fabrics"][fabric]
            self.assertEqual(row["price_cents"], locked["price_cents"])
            self.assertEqual(row["premiums_cents"], locked["premiums_cents"])

    def test_brand_is_rogers_inc_and_elemental_wood_is_etsy_only(self):
        copy = load_copy()
        public = json.dumps(public_catalog(checkout_public()), ensure_ascii=False)
        self.assertEqual(copy["seo"]["title"], "Rogers Inc Designs — Full-Bleed Anime Tees")
        self.assertTrue(copy["seo"]["meta"].startswith("Rogers Inc Designs —"))
        self.assertTrue(copy["about"].startswith("Rogers Inc Designs is the brand."))
        self.assertIn("Elemental Wood is our Etsy shop name", copy["about"])
        self.assertEqual(copy["etsy_link_label"], "Elemental Wood on Etsy")
        self.assertEqual(copy["footer"][0], "Rogers Inc Designs · designed in Australia")
        self.assertNotIn("Elemental Wood", copy["seo"]["title"])
        self.assertNotIn("Elemental Wood", copy["home"]["headline"])
        self.assertNotIn("Elemental Wood", copy["home"]["sub"])
        self.assertNotIn("Elemental Wood", " ".join(copy["footer"]))
        self.assertNotIn("Elemental Wood", copy["shop"]["intro"])
        self.assertIn("Wear the scene. Own the night.", public)
        self.assertIsNone(copy["_meta"]["contact_email"])
        self.assertIsNone(copy["_meta"]["remake_window_confirmed"])

    def test_homepage_html_uses_rogers_inc_title(self):
        html = (ROOT / "public" / "index.html").read_text(encoding="utf-8")
        self.assertIn("Rogers Inc Designs — Full-Bleed Anime Tees", html)
        self.assertIn('src="/brand/logo.png"', html)
        self.assertIn('src="/brand/mini-banner.png"', html)
        self.assertIn("Rogers Inc", html)
        self.assertNotIn("Elemental Wood", html)
        script = (ROOT / "public" / "js" / "app.js").read_text(encoding="utf-8")
        self.assertIn('src: "/brand/banner.png"', script)
        self.assertIn('alt: "Rogers Inc Designs"', script)
        for name in ("logo.png", "banner.png", "mini-banner.png"):
            self.assertTrue((ROOT / "public" / "brand" / name).is_file())

    def test_each_design_has_poly_and_cotton_mockups(self):
        catalog = load_catalog()
        public = public_catalog(checkout_public())
        visible = [item for item in catalog["products"] if catalog_listed(item)]
        self.assertEqual(len(public["products"]), len(visible))
        self.assertGreaterEqual(len(public["products"]), 8)
        full_bleed = [item for item in public["products"] if item["collection"] == "aop"]
        self.assertGreaterEqual(len(full_bleed), 8)
        for design in full_bleed:
            self.assertEqual([item["id"] for item in design["fabrics"]], ["poly"])
            self.assertEqual([item["id"] for item in design["held_fabrics"]], ["cotton"])
            self.assertEqual(design["held_fabrics"][0]["price_cents"], 7100)
            url = design["fabrics"][0]["mockup"]
            self.assertEqual(url, f"/mockups/{design['slug']}-aop-poly.jpg")
            self.assertTrue((ROOT / "public" / url.lstrip("/")).is_file())
            self.assertEqual(design["image"], url)
        originals = [item for item in full_bleed if (ROOT / "public" / "mockups" / f"{item['slug']}-aop-cotton.jpg").is_file()]
        self.assertEqual(len(originals), 7)
        self.assertNotIn("starbound-nebula-queen", {item["slug"] for item in full_bleed})
        chest = [item for item in public["products"] if item["collection"] == "chest-dtg"]
        self.assertEqual(len(chest), 7)
        for design in chest:
            self.assertEqual([item["id"] for item in design["fabrics"]], ["chest"])
            self.assertEqual(design["fabrics"][0]["price_cents"], 4700)
            self.assertTrue(design["fabrics"][0]["mockup"])
        for design in public["products"]:
            self.assertTrue(design.get("image"), design["slug"])
            image = ROOT / "public" / design["image"].lstrip("/")
            self.assertTrue(image.is_file() and image.stat().st_size > 10000, design["slug"])
            for shot in design.get("gallery") or []:
                path = ROOT / "public" / shot.lstrip("/")
                self.assertTrue(path.is_file() and path.stat().st_size > 10000, shot)

    def test_mockups_drop_the_price_caption_and_2xl_stays_the_surcharge(self):
        catalog = load_catalog()
        ronin = next(item for item in catalog["products"] if item["slug"] == "crimson-sun-last-ronin")
        self.assertEqual(unit_cents(catalog, ronin, "poly", "M"), 6500)
        self.assertEqual(unit_cents(catalog, ronin, "poly", "2XL"), 6900)
        self.assertEqual(unit_cents(catalog, ronin, "cotton", "M"), 7100)
        self.assertEqual(unit_cents(catalog, ronin, "cotton", "2XL"), 7500)
        self.assertNotEqual(unit_cents(catalog, ronin, "cotton", "2XL"), 7900)
        self.assertEqual(unit_cents(catalog, ronin, "chest", "XS"), 4700)
        self.assertEqual(unit_cents(catalog, ronin, "chest", "2XL"), 5100)
        self.assertEqual(unit_cents(catalog, ronin, "chest", "3XL"), 5400)
        css = (ROOT / "public" / "css" / "shop.css").read_text(encoding="utf-8")
        self.assertIn("aspect-ratio: 1280 / 720", css)
        mockups = list((ROOT / "public" / "mockups").glob("*-aop-*.jpg"))
        self.assertGreaterEqual(len(mockups), 16)
        for path in mockups:
            self.assertEqual(jpeg_size(path), (1280, 720), path.name)

    def test_lanes_are_data_not_a_fixed_page(self):
        public = public_catalog(checkout_public())
        ids = [item["id"] for item in public["collections"]]
        self.assertEqual(ids, ["aop", "chest-dtg", "gothic-blackletter", "fuel", "brush-smoke", "biomechanical", "living-screens", "night-shift"])
        aop = next(item for item in public["collections"] if item["id"] == "aop")
        self.assertNotIn("stoner", ids)
        self.assertEqual(aop["count"], len([item for item in public["products"] if item["collection"] == "aop"]))
        self.assertEqual(aop["sub"], "AOP Heroes")
        self.assertEqual(aop["intro"], "All-over print tees that wrap the full scene edge to edge — original anime art cut for cloth, designed in Australia.")
        screens = next(item for item in public["collections"] if item["id"] == "living-screens")
        self.assertEqual(screens["status"], "live")
        self.assertGreaterEqual(screens["count"], 10)
        self.assertIn("wallpaper packs", screens["intro"])
        screen_cards = [item for item in public["products"] if item["collection"] == "living-screens"]
        self.assertEqual(len(screen_cards), screens["count"])
        self.assertEqual(len([item for item in screen_cards if item["series"] == "crimson-sun"]), 9)
        self.assertEqual(len([item for item in screen_cards if item["series"] == "quiet-rain"]), 8)
        self.assertTrue(all(item["status"] == "live" and item["image"] for item in screen_cards))
        self.assertIn("wallpaper-quiet-ramen-steam-alley", {item["slug"] for item in screen_cards})
        self.assertIn("wallpaper-crimson-the-last-ronin", {item["slug"] for item in screen_cards})
        rain = next(item for item in public["series"] if item["id"] == "quiet-rain")
        self.assertIn("Soft weather, sharp silence", rain["blurb"])
        self.assertEqual(aop["status"], "live")
        self.assertEqual(presented_collection_status("live", 8), "ready")
        self.assertEqual(presented_collection_status("live", 10), "live")
        self.assertEqual(presented_collection_status("preview", 10), "preview")
        body = json.dumps(public)
        self.assertNotIn("letterforms with teeth", body)
        self.assertNotIn("hazy skies", body)
        self.assertNotIn("Eight designs", body)
        self.assertNotIn("8 designs", body)
        self.assertNotIn("8 tees", body)
        self.assertNotIn("First wave is live", body)
        self.assertNotIn("live store", body)
        self.assertTrue(all(item["status"] != "live" or item["count"] >= 10 for item in public["collections"]))
        self.assertEqual(public["shop"]["drops_title"], "New drops")
        self.assertEqual(public["shop"]["intro"], "Preview catalog. Each collection needs at least 10 designs before it is the storefront.")
        self.assertEqual(public["shop"]["more"], "More designs coming.")
        stored = load_catalog()
        fuel = next(item for item in public["collections"] if item["id"] == "fuel")
        self.assertEqual(fuel["count"], 10)
        self.assertEqual(fuel["status"], "live")
        self.assertEqual(fuel["landing"], "as-high-as-fuel")
        self.assertEqual(fuel["label"], "As High As Fuel")
        gothic = next(item for item in public["collections"] if item["id"] == "gothic-blackletter")
        self.assertEqual(gothic["landing"], "blackletter")
        self.assertEqual(gothic["label"], "Blackletter")
        self.assertEqual(gothic["status"], "live")
        self.assertEqual(gothic["count"], 10)
        self.assertEqual(presented_collection_status("live", 10, "gothic-blackletter"), "live")
        self.assertEqual(presented_collection_status("live", 10, "fuel"), "live")
        self.assertEqual(presented_collection_status("live", 1, "fuel"), "ready")
        self.assertEqual(next(item["label"] for item in public["collections"] if item["id"] == "aop"), "Full Bleed")
        brush = next(item for item in public["collections"] if item["id"] == "brush-smoke")
        self.assertEqual(brush["label"], "Brush & Smoke")
        self.assertEqual(brush["status"], "preview")
        self.assertEqual(brush["count"], 4)
        chest_lane = next(item for item in public["collections"] if item["id"] == "chest-dtg")
        self.assertEqual(chest_lane["status"], "ready")
        self.assertEqual(chest_lane["count"], 7)
        bio = next(item for item in public["collections"] if item["id"] == "biomechanical")
        self.assertEqual(bio["status"], "preview")
        self.assertEqual(bio["count"], 1)
        self.assertEqual(aop["count"], 21)
        self.assertEqual(aop["status"], "live")
        featured = [item["slug"] for item in public["products"] if item["collection"] == "aop" and item["status"] == "live"]
        self.assertEqual(sorted(featured), [
            "crimson-sun-last-ronin",
            "kitsune-neon-nine-tail-shrine",
            "neon-dual-blade-alley",
            "oni-mask-crimson-oni",
            "quiet-rain-umbrella-crossing",
            "quiet-rain-window-seat",
            "ronin-ghost-armour",
            "ronin-last-stand",
        ])
        fills = (
            "quiet-rain-ramen-steam-alley",
            "quiet-rain-bus-stop-downpour",
            "quiet-rain-vending-glow-puddle",
            "quiet-rain-quiet-lantern-bridge",
        )
        stored_slugs = {item["slug"]: item for item in stored["products"]}
        public_slugs = {item["slug"] for item in public["products"]}
        for slug in fills:
            self.assertEqual(stored_slugs[slug]["status"], "upcoming")
            self.assertEqual(stored_slugs[slug]["series"], "quiet-rain")
            self.assertNotIn(slug, public_slugs)
        self.assertIn("kitsune-neon-nine-tail-shrine", public_slugs)
        self.assertIn("blood-covenant", public_slugs)
        self.assertIn("too-high-to-care", public_slugs)
        self.assertIn("astral-fox-empress", public_slugs)
        self.assertNotIn("starbound-nebula-queen", public_slugs)
        self.assertIn("quiet-blade", public_slugs)
        self.assertIn("half-machine-skull", public_slugs)
        self.assertEqual(len([item for item in public["products"] if item["collection"] == "fuel"]), 10)
        self.assertTrue(all(item["status"] == "live" for item in public["products"] if item["collection"] in {"fuel", "gothic-blackletter"}))
        self.assertNotIn("chest-starbound-nebula-queen", public_slugs)
        for held in ("fuel-pump",):
            self.assertNotIn(held, public_slugs)
        fuel_card = next(item for item in public["products"] if item["slug"] == "as-high-as-fuel")
        self.assertEqual(fuel_card["status"], "live")
        self.assertEqual(fuel_card["gallery"], [
            "/mockups/as-high-as-fuel-chest.jpg",
            "/mockups/as-high-as-fuel-heather.jpg",
        ])
        for item in public["products"]:
            if item["collection"] != "fuel":
                continue
            for shot in item.get("gallery") or []:
                lowered = shot.lower()
                self.assertNotIn("black", lowered)
                self.assertNotIn("navy", lowered)
                self.assertNotIn("forest", lowered)
        self.assertEqual(fuel["sub"], "slow burns & night drives")
        self.assertTrue(all(item.get("status") == "held" for item in stored["products"] if item["slug"] in {"fuel-pump", "fuel-gauge", "fuel-stoner", "fuel-prices"}))
        received_fuel = ("premium-grade-only", "check-engine-chill-mode", "slow-lane-high-life")
        for slug in received_fuel:
            product = stored_slugs[slug]
            filename = f"Rogers-Inc-Designs-{slug}-front-4500x5400.png"
            path = ROOT / "print-ready" / "fuel" / filename
            self.assertEqual(product["print_ready"], f"fuel/{filename}")
            self.assertEqual(png_size(path), (4500, 5400))
            self.assertNotIn(filename, json.dumps(public))
        missing_print = (
            "blood-covenant",
            "iron-psalm",
            "wraith-march",
            "bone-chapel",
            "hex-altar",
            "pale-reign",
            "too-high-to-care",
            "gas-money-went-to-this",
            "budget-went-up-in-smoke",
            "running-on-fumes",
            "empty-tank-full-heart",
            "high-mileage-low-motivation",
        )
        for slug in missing_print:
            self.assertNotIn("print_ready", stored_slugs[slug])
            self.assertFalse((ROOT / "print-ready").joinpath(f"fuel/Rogers-Inc-Designs-{slug}-front-4500x5400.png").is_file())
            self.assertFalse((ROOT / "print-ready").joinpath(f"gothic/Rogers-Inc-Designs-{slug}-front-4500x5400.png").is_file())
        self.assertEqual(
            [item["label"] for item in public["series"]],
            ["Ronin Rain", "Quiet Rain", "Starbound", "Crimson Sun", "Crimson Oni", "Neon Cyberpunk", "Brush & Smoke", "Biomechanical", "New concepts", "Blackletter", "As High As Fuel"],
        )
        script = (ROOT / "public" / "js" / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "public" / "index.html").read_text(encoding="utf-8")
        self.assertIn("catalog.products", script)
        self.assertIn("catalog.collections", script)
        self.assertIn("catalog.shop.drops_title", script)
        self.assertIn("catalog.shop.more", script)
        self.assertIn("/collection/", script)
        self.assertNotIn("Eight designs", script)
        self.assertNotIn("Eight designs", html)
        self.assertNotIn("crimson-sun-last-ronin", script)
        self.assertNotIn("crimson-sun-last-ronin", html)

    def test_hooks_and_blurb_template(self):
        copy = load_copy()
        products = {item["slug"]: item for item in load_catalog()["products"]}
        self.assertEqual(products["crimson-sun-last-ronin"]["hook"], "Last man standing under a blood-red sky.")
        self.assertEqual(products["ronin-ghost-armour"]["hook"], "Empty steel that still walks.")
        self.assertEqual(products["neon-dual-blade-alley"]["hook"], "Two blades. One alley. Nowhere left to hide.")
        scene = products["quiet-rain-window-seat"]["scene"]
        poly = blurb(copy["blurb_template"], scene, "polyester")
        cotton = blurb(copy["blurb_template"], scene, "cotton")
        self.assertIn("Printed edge to edge on a polyester full-bleed tee.", poly)
        self.assertIn("Printed edge to edge on a cotton full-bleed tee.", cotton)
        self.assertIn("Original Rogers Inc Designs artwork.", poly)
        self.assertNotIn("Elemental Wood", poly)
        public = public_catalog(checkout_public())
        chest = next(item for item in public["products"] if item["slug"] == "chest-crimson-sun-last-ronin")
        self.assertIn("Chest print.", chest["blurbs"]["chest"])
        self.assertNotIn("full-bleed", chest["blurbs"]["chest"])
        self.assertEqual(chest["fabrics"][0]["price_cents"], 4700)

    def test_quote_uses_server_prices_not_client_prices(self):
        quote = quote_lines([
            {"slug": "crimson-sun-last-ronin", "fabric": "poly", "size": "M", "qty": 1, "unit_cents": 1},
            {"slug": "quiet-rain-window-seat", "fabric": "poly", "size": "2XL", "qty": 1, "price_cents": 1},
        ])
        self.assertEqual(quote["lines"][0]["unit_cents"], 6500)
        self.assertEqual(quote["lines"][1]["unit_cents"], 6900)
        self.assertEqual(quote["total_cents"], 13400)
        self.assertEqual(quote["gst_cents"], 1218)
        self.assertEqual(quote["goods_cents"], quote["total_cents"])
        self.assertNotEqual(quote["total_cents"], quote["goods_cents"] + quote["gst_cents"])
        self.assertEqual(quote["shipping_cents"], 0)
        self.assertNotIn("printful_product_id", quote["lines"][0])

    def test_launch_ladder_holds_cotton_chest_and_wallpapers(self):
        catalog = load_catalog()
        self.assertEqual(catalog["pricing"]["story"], "official-store")
        self.assertEqual(catalog["pricing"]["etsy_cents"]["poly"], 6900)
        self.assertEqual(catalog["pricing"]["etsy_cents"]["cotton"], 7500)
        self.assertEqual(catalog["pricing"]["etsy_cents"]["chest"], 4900)
        self.assertEqual(catalog["fabrics"]["poly"]["price_cents"], 6500)
        self.assertEqual(catalog["fabrics"]["cotton"]["price_cents"], 7100)
        self.assertEqual(catalog["fabrics"]["chest"]["price_cents"], 4700)
        self.assertEqual(catalog["pricing"]["wave1_cents"], {"hoodie": 7500, "aop_beanie": 4900, "flexfit": 5500})
        self.assertEqual(catalog["pricing"]["ready_art"]["short"], {})
        self.assertEqual(catalog["pricing"]["ready_art"]["at_floor"]["gothic-blackletter"], 10)
        self.assertEqual(catalog["pricing"]["ready_art"]["at_floor"]["fuel"], 10)
        self.assertEqual(catalog["pricing"]["ready_art"]["at_floor"]["crimson-sun"], 10)
        self.assertEqual(catalog["pricing"]["ready_art"]["at_floor"]["quiet-rain"], 10)
        self.assertEqual(catalog["pricing"]["ready_art"]["at_floor"]["living-screens"], 57)
        self.assertEqual(catalog["pricing"]["ready_art"]["priority"], [])
        public_body = json.dumps(public_catalog(checkout_public()))
        self.assertNotIn("etsy_cents", public_body)
        self.assertIn("Official store", public_body)
        chest = catalog["fabrics"]["chest"]
        self.assertEqual(chest["status"], "live")
        self.assertNotIn("4XL", chest["sizes"])
        self.assertNotIn("5XL", chest["sizes"])
        public = public_catalog(checkout_public())
        self.assertEqual(public["offer"]["hero_fabric"], "poly")
        self.assertEqual(public["addons"][0]["with_shirt_cents"], 1000)
        self.assertEqual(public["addons"][0]["status"], "held")
        chest_quote = quote_lines([{"slug": "chest-crimson-sun-last-ronin", "fabric": "chest", "size": "M", "qty": 1}])
        self.assertEqual(chest_quote["lines"][0]["unit_cents"], 4700)
        chest_2xl = quote_lines([{"slug": "chest-crimson-sun-last-ronin", "fabric": "chest", "size": "3XL", "qty": 1}])
        self.assertEqual(chest_2xl["lines"][0]["unit_cents"], 5400)
        preview_quote = quote_lines([{"slug": "void-king", "fabric": "chest", "size": "M", "qty": 1}])
        self.assertEqual(preview_quote["lines"][0]["unit_cents"], 4700)
        fuel_quote = quote_lines([{"slug": "as-high-as-fuel", "fabric": "chest", "size": "M", "qty": 1}])
        self.assertEqual(fuel_quote["lines"][0]["unit_cents"], 4700)
        slogan = quote_lines([{"slug": "too-high-to-care", "fabric": "chest", "size": "M", "qty": 1}])
        self.assertEqual(slogan["lines"][0]["unit_cents"], 4700)
        with self.assertRaises(ShopError):
            quote_lines([{"slug": "fuel-pump", "fabric": "chest", "size": "M", "qty": 1}])
        with self.assertRaises(ShopError):
            quote_lines([{"slug": "starbound-nebula-queen", "fabric": "poly", "size": "M", "qty": 1}])
        with self.assertRaises(ShopError):
            quote_lines([{"slug": "chest-starbound-nebula-queen", "fabric": "chest", "size": "M", "qty": 1}])
        wallpaper = quote_lines([{"slug": "wallpaper-crimson-the-last-ronin", "fabric": "wallpaper", "size": "Download", "qty": 1}])
        self.assertEqual(wallpaper["lines"][0]["unit_cents"], 1200)
        quiet_wall = quote_lines([{"slug": "wallpaper-quiet-ramen-steam-alley", "fabric": "wallpaper", "size": "Download", "qty": 1}])
        self.assertEqual(quiet_wall["lines"][0]["unit_cents"], 1200)
        fox = quote_lines([{"slug": "astral-fox-empress", "fabric": "poly", "size": "M", "qty": 1}])
        self.assertEqual(fox["lines"][0]["unit_cents"], 6500)
        blade = quote_lines([{"slug": "quiet-blade", "fabric": "chest", "size": "M", "qty": 1}])
        self.assertEqual(blade["lines"][0]["unit_cents"], 4700)
        skull = quote_lines([{"slug": "half-machine-skull", "fabric": "chest", "size": "M", "qty": 1}])
        self.assertEqual(skull["lines"][0]["unit_cents"], 4700)
        with self.assertRaises(ShopError):
            quote_lines([{"slug": "crimson-sun-last-ronin", "fabric": "cotton", "size": "M", "qty": 1}])
        with self.assertRaises(ShopError):
            quote_lines([{
                "slug": "crimson-sun-last-ronin",
                "fabric": "poly",
                "size": "M",
                "qty": 1,
                "addon": "wallpaper-bundle",
            }])
        with self.assertRaises(ShopError):
            quote_lines([{"slug": "crimson-sun-last-ronin", "fabric": "poly", "size": "4XL", "qty": 1}])
        with self.assertRaises(ShopError):
            settle([], "US")

    def test_customer_must_be_in_australia(self):
        with self.assertRaises(Exception):
            validate_customer({"name": "A", "email": "a@b.co", "line1": "1 Road", "suburb": "Gladstone", "state": "QLD", "postcode": "4680"})
        with self.assertRaises(Exception):
            validate_customer({"name": "Ada", "email": "ada@example.com", "line1": "1 Road", "suburb": "Town", "state": "NY", "postcode": "4680"})
        customer = validate_customer({
            "name": "Ada Rogers",
            "email": "ada@example.com",
            "line1": "12 Goondoon Street",
            "suburb": "Gladstone",
            "state": "qld",
            "postcode": "4680",
        })
        self.assertEqual(customer["country"], "AU")
        self.assertEqual(customer["state"], "QLD")


class CheckoutTests(unittest.TestCase):
    def setUp(self):
        self.saved = snapshot_env()
        clear_payment_env()
        self.orders = ROOT / "tests" / "tmp-orders"
        self.orders.mkdir(exist_ok=True)
        for path in self.orders.glob("*.json"):
            path.unlink()
        os.environ["SHOP_ORDERS"] = str(self.orders)

    def tearDown(self):
        restore_env(self.saved)
        for path in self.orders.glob("*.json"):
            path.unlink()

    def customer(self):
        return {
            "name": "Ada Rogers",
            "email": "ada@example.com",
            "line1": "12 Goondoon Street",
            "suburb": "Gladstone",
            "state": "QLD",
            "postcode": "4680",
        }

    def lines(self):
        return [{"slug": "oni-mask-crimson-oni", "fabric": "poly", "size": "L", "qty": 2}]

    def test_demo_takes_no_payment_and_does_not_print(self):
        os.environ["SHOP_CHECKOUT"] = "demo"
        with mock.patch("store.checkout._stripe_request", side_effect=AssertionError("stripe called")):
            view = place_order(self.orders, self.lines(), self.customer(), base_url="http://127.0.0.1:8765")
        self.assertEqual(view["mode"], "demo")
        self.assertFalse(view["payment_taken"])
        self.assertFalse(view["print_or_ship"])
        self.assertFalse(view["automatic_print"])
        self.assertIn("no payment will be taken and no shirt will be printed or shipped", view["notice"]["text"])
        saved = json.loads(next(self.orders.glob("*.json")).read_text(encoding="utf-8"))
        self.assertEqual(saved["lines"][0]["printful_product_id"], 257)
        self.assertEqual(saved["lines"][0]["line_cents"], 13000)
        self.assertEqual(view["gst_cents"], 1182)
        self.assertEqual(view["total_cents"], 13000)
        self.assertNotIn("printful_product_id", view["lines"][0])
        self.assertIn("not instant auto-push", saved["internal_note"])

    def test_payid_holds_the_order(self):
        os.environ["SHOP_PAYID"] = "rogers@example"
        os.environ["SHOP_CHECKOUT"] = "demo"
        view = place_order(self.orders, self.lines(), self.customer(), base_url="http://127.0.0.1")
        self.assertEqual(checkout_mode(), "payid")
        self.assertEqual(view["status"], "awaiting_payment")
        self.assertEqual(view["payid"], "rogers@example")
        self.assertEqual(view["payid_name"], "Rogers Inc Designs")
        self.assertFalse(view["payment_taken"])
        self.assertFalse(view["print_or_ship"])

    def test_off_mode_does_not_write_an_order(self):
        from store.catalog import ShopError

        with self.assertRaises(ShopError) as caught:
            place_order(self.orders, self.lines(), self.customer(), base_url="http://127.0.0.1")
        self.assertEqual(caught.exception.status, 409)
        self.assertEqual(list(self.orders.glob("*.json")), [])
        self.assertIn("No payment will be taken", str(caught.exception))

    def test_stripe_form_uses_locked_cents(self):
        order = {
            "id": "RID-AABBCCDD",
            "customer": {"email": "ada@example.com"},
            "lines": [{
                "listing_name": "Crimson Sun: The Last Ronin",
                "fabric_label": "Polyester",
                "size": "2XL",
                "qty": 1,
                "unit_cents": 6900,
            }],
        }
        fields = dict(stripe_fields(order, "https://shop.example"))
        self.assertEqual(fields["line_items[0][price_data][unit_amount]"], "6900")
        self.assertEqual(fields["line_items[0][price_data][currency]"], "aud")
        self.assertEqual(fields["line_items[0][price_data][tax_behavior]"], "inclusive")
        self.assertEqual(fields["automatic_tax[enabled]"], "false")
        self.assertNotIn("line_items[1][price_data][unit_amount]", fields)
        name = fields["line_items[0][price_data][product_data][name]"]
        self.assertIn("Crimson Sun: The Last Ronin", name)
        self.assertIn("Polyester", name)
        self.assertIn("2XL", name)
        self.assertEqual(fields["shipping_address_collection[allowed_countries][0]"], "AU")
        self.assertNotIn("shipping_address_collection[allowed_countries][1]", fields)
        self.assertEqual(fields["shipping_options[0][shipping_rate_data][fixed_amount][amount]"], "0")
        self.assertEqual(fields["shipping_options[0][shipping_rate_data][display_name]"], "Free shipping in Australia")
        self.assertNotIn("shipping_options[1][shipping_rate_data][fixed_amount][amount]", fields)
        self.assertEqual(
            fields["success_url"],
            "https://shop.example/order/RID-AABBCCDD?session_id={CHECKOUT_SESSION_ID}",
        )
        self.assertEqual(fields["cancel_url"], "https://shop.example/checkout?cancelled=1")
        body = _form_body(list(fields.items())).decode()
        self.assertIn("{CHECKOUT_SESSION_ID}", body)
        self.assertNotIn("%7BCHECKOUT_SESSION_ID%7D", body)

    def test_stripe_test_key_opens_checkout_and_live_key_does_not(self):
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_example"
        os.environ["SHOP_PAYID"] = "rogers@example"
        self.assertEqual(checkout_mode(), "stripe")
        captured = {}

        def fake(path, secret, fields=None):
            captured["path"] = path
            captured["secret"] = secret
            captured["fields"] = dict(fields or [])
            return {"id": "cs_test_1", "url": "https://checkout.stripe.com/c/pay/cs_test_1"}

        with mock.patch("store.checkout._stripe_request", side_effect=fake):
            view = place_order(
                self.orders,
                [{"slug": "crimson-sun-last-ronin", "fabric": "poly", "size": "2XL", "qty": 1}],
                self.customer(),
                base_url="http://127.0.0.1:8765",
            )
        self.assertEqual(view["url"], "https://checkout.stripe.com/c/pay/cs_test_1")
        self.assertEqual(view["status"], "pending_payment")
        self.assertFalse(view["payment_taken"])
        self.assertFalse(view["print_or_ship"])
        self.assertEqual(view["total_cents"], 6900)
        self.assertEqual(captured["secret"], "sk_test_example")
        self.assertEqual(captured["fields"]["line_items[0][price_data][unit_amount]"], "6900")
        self.assertEqual(captured["fields"]["automatic_tax[enabled]"], "false")
        self.assertIn("2XL", captured["fields"]["line_items[0][price_data][product_data][name]"])
        self.assertIn("Polyester", captured["fields"]["line_items[0][price_data][product_data][name]"])

        os.environ["STRIPE_SECRET_KEY"] = "sk_live_example"
        with mock.patch("store.checkout._stripe_request", side_effect=AssertionError("live stripe called")):
            with self.assertRaises(ShopError) as caught:
                place_order(self.orders, self.lines(), self.customer(), base_url="http://127.0.0.1:8765")
        self.assertEqual(caught.exception.status, 409)
        self.assertIn("test secret", str(caught.exception))

    def test_confirm_stripe_accepts_the_inclusive_total_only(self):
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_example"
        sessions = {
            "create": {"id": "cs_test_paid", "url": "https://checkout.stripe.com/c/pay/cs_test_paid"},
        }

        def fake(path, secret, fields=None):
            if fields is None:
                return sessions["retrieve"]
            return sessions["create"]

        with mock.patch("store.checkout._stripe_request", side_effect=fake):
            view = place_order(
                self.orders,
                [{"slug": "crimson-sun-last-ronin", "fabric": "poly", "size": "M", "qty": 1}],
                self.customer(),
                base_url="https://shop.example",
            )
            sessions["retrieve"] = {
                "id": "cs_test_paid",
                "payment_status": "unpaid",
                "amount_total": 6500,
                "currency": "aud",
            }
            pending = confirm_stripe(self.orders, view["id"], "cs_test_paid", "sk_test_example")
            self.assertFalse(pending["payment_taken"])
            sessions["retrieve"] = {
                "id": "cs_test_paid",
                "payment_status": "paid",
                "amount_total": 7091,
                "currency": "aud",
                "total_details": {"amount_shipping": 0, "amount_tax": 591},
            }
            with self.assertRaises(ShopError):
                confirm_stripe(self.orders, view["id"], "cs_test_paid", "sk_test_example")
            sessions["retrieve"] = {
                "id": "cs_test_paid",
                "payment_status": "paid",
                "amount_total": 6500,
                "currency": "aud",
                "total_details": {"amount_shipping": 0, "amount_tax": 0},
                "shipping_details": {"address": {"country": "US"}},
            }
            with self.assertRaises(ShopError):
                confirm_stripe(self.orders, view["id"], "cs_test_paid", "sk_test_example")
            sessions["retrieve"] = {
                "id": "cs_test_paid",
                "payment_status": "paid",
                "amount_total": 6500,
                "currency": "aud",
                "total_details": {"amount_shipping": 0, "amount_tax": 0},
                "shipping_details": {"address": {"country": "AU"}},
            }
            paid = confirm_stripe(self.orders, view["id"], "cs_test_paid", "sk_test_example")
        self.assertTrue(paid["payment_taken"])
        self.assertFalse(paid["print_or_ship"])
        self.assertEqual(paid["total_cents"], 6500)
        self.assertEqual(paid["gst_cents"], 591)


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.saved = snapshot_env()
        clear_payment_env()
        self.orders = ROOT / "tests" / "tmp-orders-http"
        self.orders.mkdir(exist_ok=True)
        for path in self.orders.glob("*.json"):
            path.unlink()
        os.environ["SHOP_CHECKOUT"] = "demo"
        os.environ["SHOP_ORDERS"] = str(self.orders)
        self.server = make_server(0, "127.0.0.1", self.orders)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=3)
        self.server.server_close()
        restore_env(self.saved)
        for path in self.orders.glob("*.json"):
            path.unlink()

    def get(self, path):
        with urllib.request.urlopen(self.base + path) as response:
            return response.status, response.read().decode()

    def post(self, path, payload):
        request = urllib.request.Request(
            self.base + path,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode())

    def test_catalog_and_demo_checkout_round_trip(self):
        status, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("Rogers Inc Designs — Full-Bleed Anime Tees", body)
        self.assertNotIn("Elemental Wood", body)
        catalog = json.loads(self.get("/api/catalog")[1])
        self.assertEqual(catalog["checkout"]["mode"], "demo")
        self.assertEqual(catalog["products"][0]["fabrics"][0]["price_cents"], 6500)
        self.assertGreater(len(catalog["products"]), 0)
        self.assertNotIn("Eight designs", self.get("/api/catalog")[1])
        self.assertIn("More designs coming.", self.get("/api/catalog")[1])
        self.assertIn("gothic-blackletter", [item["id"] for item in catalog["collections"]])
        self.assertIn("as-high-as-fuel", [item["landing"] for item in catalog["collections"]])
        self.assertIn("As High As Fuel", self.get("/api/catalog")[1])
        self.assertEqual(catalog["products"][0]["fabrics"][0]["id"], "poly")
        self.assertEqual(catalog["products"][0]["held_fabrics"][0]["id"], "cotton")
        self.assertIn("no shirt will be printed", catalog["checkout"]["demo_lead"])
        view = self.post("/api/checkout", {
            "lines": [{"slug": "crimson-sun-last-ronin", "fabric": "poly", "size": "XS", "qty": 1}],
            "customer": {
                "name": "Ada Rogers",
                "email": "ada@example.com",
                "line1": "12 Goondoon Street",
                "suburb": "Gladstone",
                "state": "QLD",
                "postcode": "4680",
            },
        })
        self.assertFalse(view["payment_taken"])
        self.assertFalse(view["print_or_ship"])
        loaded = json.loads(self.get(f"/api/orders/{view['id']}")[1])
        self.assertEqual(loaded["total_cents"], 6500)
        status, leaked = self.get("/catalog.json")
        self.assertEqual(status, 200)
        self.assertNotIn("printful_product_id", leaked)


if __name__ == "__main__":
    unittest.main()
