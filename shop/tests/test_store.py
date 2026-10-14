"""Prices, Marketing copy, and checkout honesty for the Rogers Inc Designs shop."""

import json
import os
import threading
import unittest
import urllib.error
import urllib.parse
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
from store.server import _orders_dir, bind_address, make_server  # noqa: E402

ENV_KEYS = (
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "STRIPE_PUBLISHABLE_KEY",
    "SHOP_PAYID",
    "SHOP_PAYID_NAME",
    "SHOP_CHECKOUT",
    "SHOP_ORDERS",
    "SHOP_ORDERS_DIR",
    "SHOP_BASE_URL",
    "PORT",
    "SHOP_PORT",
    "SHOP_HOST",
    "SHOP_ADMIN_PASSWORD",
    "PRINTFUL_API_KEY",
    "PRINTFUL_STORE_ID",
    "PRINTFUL_AUTO_CONFIRM",
    "SHOP_ALERT_EMAIL",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USER",
    "SMTP_PASS",
    "SMTP_FROM",
    "SHOP_FROM_EMAIL",
    "BREVO_API_KEY",
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
        self.assertEqual(copy["_meta"]["contact_email"], "rogersinc426@gmail.com")
        self.assertEqual(copy["_meta"]["remake_window_confirmed"], "within 7 days of delivery")

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
            if design["slug"] == "starbound-nebula-queen":
                self.assertEqual(url, "/mockups/nebula-queen-nudge-down-shirt-mockup.jpg")
            else:
                self.assertEqual(url, f"/mockups/{design['slug']}-aop-poly.jpg")
            self.assertTrue((ROOT / "public" / url.lstrip("/")).is_file())
            self.assertEqual(design["image"], url)
        originals = [item for item in full_bleed if (ROOT / "public" / "mockups" / f"{item['slug']}-aop-cotton.jpg").is_file()]
        self.assertEqual(len(originals), 7)
        nebula = next(item for item in full_bleed if item["slug"] == "starbound-nebula-queen")
        nudge = "/mockups/nebula-queen-nudge-down-shirt-mockup.jpg"
        self.assertEqual(nebula["status"], "live")
        self.assertEqual(nebula["series"], "starbound-sirens")
        self.assertEqual(nebula["fabrics"][0]["id"], "poly")
        self.assertEqual(nebula["fabrics"][0]["price_cents"], 6500)
        self.assertEqual(nebula["fabrics"][0]["mockup"], nudge)
        self.assertEqual(nebula["fabrics"][0]["etsy_url"], "https://www.etsy.com/listing/4589654524")
        self.assertEqual(nebula["held_fabrics"][0]["id"], "cotton")
        self.assertEqual(nebula["held_fabrics"][0]["price_cents"], 7100)
        self.assertEqual(nebula["held_fabrics"][0]["mockup"], nudge)
        self.assertEqual(nebula["held_fabrics"][0]["etsy_url"], "https://www.etsy.com/listing/4589718938")
        self.assertEqual(nebula["gallery"], [nudge])
        self.assertEqual(jpeg_size(ROOT / "public" / nudge.lstrip("/")), (1280, 720))
        print_name = "Rogers-Inc-Designs-starbound-nebula-queen-aop-nudge-down-4500x5400.png"
        print_path = ROOT / "print-ready" / "aop" / print_name
        stored_nebula = next(item for item in catalog["products"] if item["slug"] == "starbound-nebula-queen")
        self.assertEqual(stored_nebula["print_ready"], f"aop/{print_name}")
        self.assertEqual(png_size(print_path), (4500, 5400))
        self.assertEqual(print_path.read_bytes()[25], 2)
        public_body = json.dumps(public)
        for banned in (
            "starbound-nebula-queen-aop-poly.jpg",
            "starbound-nebula-queen-aop-cotton.jpg",
            "aop-centered",
            "aop-fill",
            "chest-starbound-nebula-queen",
            print_name,
        ):
            self.assertNotIn(banned, public_body)
        chest = [item for item in public["products"] if item["collection"] == "chest-dtg"]
        self.assertEqual(len(chest), 10)
        self.assertEqual(
            {design["slug"] for design in chest},
            {
                "chest-crimson-sun-last-ronin",
                "chest-oni-mask-crimson-oni",
                "chest-quiet-rain-umbrella-crossing",
                "chest-quiet-rain-window-seat",
                "chest-neon-dual-blade-alley",
                "chest-ronin-ghost-armour",
                "chest-ronin-last-stand",
                "chest-kitsune-neon-nine-tail-shrine",
                "chest-tengu-storm-chrome-crow",
                "chest-astral-fox-empress",
            },
        )
        for design in chest:
            self.assertEqual(design["status"], "live", design["slug"])
            self.assertTrue(design["image"].endswith(f"{design['slug']}-chest.jpg"))
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
        self.assertEqual(chest_lane["status"], "live")
        self.assertEqual(chest_lane["count"], 10)
        bio = next(item for item in public["collections"] if item["id"] == "biomechanical")
        self.assertEqual(bio["status"], "preview")
        self.assertEqual(bio["count"], 1)
        self.assertEqual(aop["count"], 22)
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
            "starbound-nebula-queen",
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
        self.assertIn("starbound-nebula-queen", public_slugs)
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
        received_print = {
            "fuel": (
                "too-high-to-care",
                "gas-money-went-to-this",
                "budget-went-up-in-smoke",
                "running-on-fumes",
                "empty-tank-full-heart",
                "high-mileage-low-motivation",
                "premium-grade-only",
                "check-engine-chill-mode",
                "slow-lane-high-life",
            ),
            "gothic": (
                "blood-covenant",
                "iron-psalm",
                "wraith-march",
                "bone-chapel",
                "hex-altar",
                "pale-reign",
                "void-king",
                "ash-iron",
                "night-warden",
                "grave-shift",
            ),
        }
        for lane, slugs in received_print.items():
            for slug in slugs:
                product = stored_slugs[slug]
                filename = f"Rogers-Inc-Designs-{slug}-front-4500x5400.png"
                path = ROOT / "print-ready" / lane / filename
                self.assertEqual(product["print_ready"], f"{lane}/{filename}")
                self.assertEqual(png_size(path), (4500, 5400))
                self.assertEqual(path.read_bytes()[25], 2)
                self.assertNotIn(filename, json.dumps(public))
        fuel_front = "Rogers-Inc-Designs-as-high-as-fuel-front-4500x5400.png"
        fuel_front_path = ROOT / "print-ready" / "fuel" / fuel_front
        self.assertEqual(stored_slugs["as-high-as-fuel"]["print_ready"], f"fuel/{fuel_front}")
        self.assertEqual(png_size(fuel_front_path), (4500, 5400))
        self.assertNotIn(fuel_front, json.dumps(public))
        fuel_dark = ROOT / "print-ready" / "fuel" / "Rogers-Inc-Designs-as-high-as-fuel-dark-front-4500x5400.png"
        self.assertEqual(png_size(fuel_dark), (4500, 5400))
        self.assertNotIn("as-high-as-fuel-dark", json.dumps(public))
        pending_chest_print = {
            "chest-kitsune-neon-nine-tail-shrine": "chest/Rogers-Inc-Designs-kitsune-neon-nine-tail-shrine-front-4500x5400.png",
            "chest-tengu-storm-chrome-crow": "chest/Rogers-Inc-Designs-tengu-storm-chrome-crow-front-4500x5400.png",
            "chest-astral-fox-empress": "chest/Rogers-Inc-Designs-astral-fox-empress-front-4500x5400.png",
        }
        for slug, relative in pending_chest_print.items():
            path = ROOT / "print-ready" / relative
            self.assertEqual(stored_slugs[slug]["status"], "live")
            self.assertEqual(stored_slugs[slug]["print_ready"], relative)
            self.assertEqual(png_size(path), (4500, 5400))
            self.assertEqual(path.read_bytes()[25], 2)
            self.assertNotIn(path.name, json.dumps(public))
        missing_print = ()
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
        nebula_quote = quote_lines([{"slug": "starbound-nebula-queen", "fabric": "poly", "size": "M", "qty": 1}])
        self.assertEqual(nebula_quote["lines"][0]["unit_cents"], 6500)
        nebula_2xl = quote_lines([{"slug": "starbound-nebula-queen", "fabric": "poly", "size": "2XL", "qty": 1}])
        self.assertEqual(nebula_2xl["lines"][0]["unit_cents"], 6900)
        with self.assertRaises(ShopError):
            quote_lines([{"slug": "chest-starbound-nebula-queen", "fabric": "chest", "size": "M", "qty": 1}])
        for slug in (
            "chest-kitsune-neon-nine-tail-shrine",
            "chest-tengu-storm-chrome-crow",
            "chest-astral-fox-empress",
        ):
            quoted = quote_lines([{"slug": slug, "fabric": "chest", "size": "M", "qty": 1}])
            self.assertEqual(quoted["lines"][0]["unit_cents"], 4700)
        with self.assertRaises(ShopError):
            quote_lines([{"slug": "starbound-nebula-queen", "fabric": "cotton", "size": "M", "qty": 1}])
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
        pending = quote_lines(
            [{"slug": "crimson-sun-last-ronin", "fabric": "poly", "size": "M", "qty": 1}],
            {"country": "US"},
        )
        self.assertTrue(pending["postage_pending"])
        self.assertEqual(pending["lines"][0]["unit_cents"], 6500)
        self.assertNotIn("Enter the name", json.dumps(pending))

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
        self._clear_orders()
        os.environ["SHOP_ORDERS"] = str(self.orders)

    def tearDown(self):
        restore_env(self.saved)
        self._clear_orders()

    def _clear_orders(self):
        for path in self.orders.glob("*.json"):
            path.unlink()
        idem = self.orders / "idempotency"
        if idem.is_dir():
            for path in idem.glob("*.json"):
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

    def test_same_checkout_key_does_not_create_a_second_order(self):
        os.environ["SHOP_PAYID"] = "rogers@example"
        first = place_order(
            self.orders,
            self.lines(),
            self.customer(),
            base_url="http://127.0.0.1",
            idempotency_key="checkout-key-1111",
        )
        second = place_order(
            self.orders,
            self.lines(),
            self.customer(),
            base_url="http://127.0.0.1",
            idempotency_key="checkout-key-1111",
        )
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(list(self.orders.glob("RID-*.json"))), 1)
        other = place_order(
            self.orders,
            self.lines(),
            self.customer(),
            base_url="http://127.0.0.1",
            idempotency_key="checkout-key-2222",
        )
        self.assertNotEqual(other["id"], first["id"])
        self.assertEqual(len(list(self.orders.glob("RID-*.json"))), 2)
        with self.assertRaises(ShopError):
            place_order(
                self.orders,
                self.lines(),
                self.customer(),
                base_url="http://127.0.0.1",
                idempotency_key="../escape",
            )

    def test_brevo_sends_over_https_and_smtp_is_the_fallback(self):
        from store.mail import send_email

        os.environ["BREVO_API_KEY"] = "xkeysib-test"
        os.environ["SHOP_FROM_EMAIL"] = "rogersinc426@gmail.com"
        captured = {}

        class Response:
            def read(self):
                return b'{"messageId":"<1@brevo>"}'

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def fake_urlopen(request, timeout=None):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            captured["headers"] = {key.lower(): value for key, value in request.header_items()}
            captured["body"] = json.loads(request.data.decode())
            return Response()

        with mock.patch("store.mail.urllib.request.urlopen", fake_urlopen):
            with mock.patch("store.mail.smtplib.SMTP", side_effect=AssertionError("smtp called")):
                with self.assertLogs("store", level="WARNING") as logs:
                    sent = send_email(
                        "ada@example.com",
                        "We received your order",
                        "Hello",
                        reference="RID-D48B65CB",
                    )
        self.assertTrue(sent)
        self.assertEqual(captured["url"], "https://api.brevo.com/v3/smtp/email")
        self.assertEqual(captured["timeout"], 8)
        self.assertEqual(captured["headers"]["api-key"], "xkeysib-test")
        self.assertEqual(captured["body"]["sender"]["name"], "Rogers Inc Designs")
        self.assertEqual(captured["body"]["sender"]["email"], "rogersinc426@gmail.com")
        self.assertEqual(captured["body"]["to"], [{"email": "ada@example.com"}])
        self.assertEqual(captured["body"]["textContent"], "Hello")
        text = " ".join(logs.output)
        self.assertIn("email attempt order=RID-D48B65CB", text)
        self.assertIn("email sent order=RID-D48B65CB to=ada@example.com via=brevo", text)

        os.environ["SMTP_FROM"] = "from@example.com"
        with mock.patch("store.mail.urllib.request.urlopen", fake_urlopen):
            send_email("ada@example.com", "Subject", "Body", reference="RID-D48B65CB")
        self.assertEqual(captured["body"]["sender"]["email"], "from@example.com")

        os.environ["SMTP_HOST"] = "smtp.test"
        os.environ["SMTP_PORT"] = "587"
        os.environ["SMTP_USER"] = "rogersinc426@gmail.com"
        os.environ["SMTP_PASS"] = "fake-app-password"

        class FakeSMTP:
            opened = []

            def __init__(self, host, port, timeout=None):
                self.host = host
                self.messages = []
                FakeSMTP.opened.append(self)

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def ehlo(self):
                return None

            def starttls(self, context=None):
                return None

            def login(self, user, password):
                return None

            def send_message(self, message):
                self.messages.append(message)

        with mock.patch("store.mail.urllib.request.urlopen", side_effect=OSError("Network is unreachable")):
            with mock.patch("store.mail.smtplib.SMTP", FakeSMTP):
                with self.assertLogs("store", level="WARNING") as logs:
                    fallback = send_email("ada@example.com", "Subject", "Body", reference="RID-D48B65CB")
        self.assertTrue(fallback)
        self.assertEqual(FakeSMTP.opened[0].host, "smtp.test")
        self.assertEqual(len(FakeSMTP.opened[0].messages), 1)
        self.assertIn("via=smtp", " ".join(logs.output))
        self.assertIn("order=RID-D48B65CB", " ".join(logs.output))

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

    def test_card_sits_beside_payid_and_live_keys_open_checkout(self):
        from store.checkout import card_available

        os.environ["STRIPE_SECRET_KEY"] = "sk_test_example"
        os.environ["SHOP_PAYID"] = "rogers@example"
        self.assertEqual(checkout_mode(), "payid")
        self.assertTrue(card_available())
        public = checkout_public()
        self.assertTrue(public["card"])
        self.assertTrue(public["payid_available"])
        self.assertNotIn("sk_test_example", json.dumps(public))
        held = place_order(
            self.orders,
            [{"slug": "crimson-sun-last-ronin", "fabric": "poly", "size": "2XL", "qty": 1}],
            self.customer(),
            base_url="http://127.0.0.1:8765",
        )
        self.assertEqual(held["mode"], "payid")
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
                payment="card",
            )
        self.assertEqual(view["url"], "https://checkout.stripe.com/c/pay/cs_test_1")
        self.assertEqual(view["mode"], "stripe")
        self.assertEqual(view["status"], "pending_payment")
        self.assertFalse(view["payment_taken"])
        self.assertFalse(view["print_or_ship"])
        self.assertEqual(view["total_cents"], 6900)
        self.assertEqual(captured["secret"], "sk_test_example")
        self.assertEqual(captured["fields"]["line_items[0][price_data][unit_amount]"], "6900")
        self.assertEqual(captured["fields"]["line_items[0][price_data][currency]"], "aud")
        self.assertEqual(captured["fields"]["automatic_tax[enabled]"], "false")
        self.assertEqual(captured["fields"]["shipping_options[0][shipping_rate_data][fixed_amount][amount]"], "0")
        self.assertIn("2XL", captured["fields"]["line_items[0][price_data][product_data][name]"])
        self.assertIn("Polyester", captured["fields"]["line_items[0][price_data][product_data][name]"])

        os.environ["STRIPE_SECRET_KEY"] = "sk_live_example"
        with mock.patch("store.checkout._stripe_request", side_effect=fake):
            live = place_order(
                self.orders,
                self.lines(),
                self.customer(),
                base_url="http://127.0.0.1:8765",
                payment="card",
            )
        self.assertEqual(live["mode"], "stripe")
        self.assertEqual(captured["secret"], "sk_live_example")

        os.environ["STRIPE_SECRET_KEY"] = "pk_test_not_a_secret"
        self.assertFalse(card_available())
        from store.checkout import warn_stripe_secret
        with self.assertLogs("store", level="WARNING") as caught:
            warn_stripe_secret()
        self.assertIn("publishable key", " ".join(caught.output))
        self.assertIn("pk_", " ".join(caught.output))
        with mock.patch("store.checkout._stripe_request", side_effect=AssertionError("stripe called")):
            with self.assertRaises(ShopError) as caught:
                place_order(self.orders, self.lines(), self.customer(), base_url="http://127.0.0.1:8765", payment="card")
        self.assertEqual(caught.exception.status, 409)

    def test_overseas_card_adds_printful_postage_and_payid_cannot_pay_it(self):
        os.environ["SHOP_PAYID"] = "rogers@example"
        overseas = {
            "name": "Ada Rogers",
            "email": "ada@example.com",
            "line1": "1600 Pennsylvania Avenue",
            "suburb": "Washington",
            "state": "DC",
            "postcode": "20500",
            "country": "US",
        }
        with self.assertRaises(ShopError) as missing:
            place_order(self.orders, self.lines(), overseas, base_url="http://127.0.0.1:8765")
        self.assertEqual(missing.exception.status, 409)
        self.assertIn("Card checkout is not switched on", str(missing.exception))
        self.assertEqual(list(self.orders.glob("*.json")), [])

        os.environ["STRIPE_SECRET_KEY"] = "sk_test_example"
        os.environ["PRINTFUL_API_KEY"] = "printful-test-token"

        def rates(recipient, items, env):
            self.assertEqual(recipient["country_code"], "US")
            self.assertEqual(recipient["state_code"], "DC")
            self.assertEqual(items[0]["variant_id"], 8853)
            self.assertEqual(env["PRINTFUL_API_KEY"], "printful-test-token")
            return [{"id": "STANDARD", "name": "Flat Rate", "rate": "18.40", "currency": "AUD"}]

        captured = {}

        def fake(path, secret, fields=None):
            captured["fields"] = dict(fields or [])
            captured["secret"] = secret
            return {"id": "cs_test_os", "url": "https://checkout.stripe.com/c/pay/cs_test_os"}

        with mock.patch("store.printful.shipping_rates", side_effect=rates):
            with self.assertRaises(ShopError) as blocked:
                place_order(
                    self.orders,
                    [{"slug": "crimson-sun-last-ronin", "fabric": "poly", "size": "L", "qty": 1}],
                    overseas,
                    base_url="https://shop.example",
                    payment="payid",
                )
        self.assertIn("pay by card", str(blocked.exception).lower())
        with mock.patch("store.printful.shipping_rates", side_effect=rates):
            with mock.patch("store.checkout._stripe_request", side_effect=fake):
                view = place_order(
                    self.orders,
                    [{"slug": "crimson-sun-last-ronin", "fabric": "poly", "size": "L", "qty": 1}],
                    overseas,
                    base_url="https://shop.example",
                    payment="card",
                )
        self.assertEqual(view["mode"], "stripe")
        self.assertEqual(view["shipping_cents"], 1840)
        self.assertEqual(view["total_cents"], 6500 + 1840)
        self.assertEqual(view["gst_cents"], 0)
        self.assertEqual(captured["fields"]["shipping_options[0][shipping_rate_data][fixed_amount][amount]"], "1840")
        self.assertEqual(captured["fields"]["line_items[0][price_data][currency]"], "aud")
        self.assertNotIn("shipping_address_collection[allowed_countries][0]", captured["fields"])
        self.assertNotIn("shipping_options[1][shipping_rate_data][fixed_amount][amount]", captured["fields"])
        saved = json.loads((self.orders / f"{view['id']}.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["customer"]["country"], "US")
        self.assertEqual(saved["printful_shipping"], "STANDARD")
        from store.printful import order_payload

        payload = order_payload(saved, [{"variant_id": 8853, "quantity": 1}])
        self.assertEqual(payload["recipient"]["country_code"], "US")
        self.assertEqual(payload["recipient"]["city"], "Washington")
        self.assertEqual(payload["recipient"]["state_code"], "DC")
        self.assertEqual(payload["shipping"], "STANDARD")

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
        idem = self.orders / "idempotency"
        if idem.is_dir():
            for path in idem.glob("*.json"):
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
        idem = self.orders / "idempotency"
        if idem.is_dir():
            for path in idem.glob("*.json"):
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

    def post_form(self, path, fields, cookie=""):
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if cookie:
            headers["Cookie"] = cookie
        request = urllib.request.Request(
            self.base + path,
            data=urllib.parse.urlencode(fields).encode(),
            headers=headers,
        )
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, response.headers, response.read().decode()
        except urllib.error.HTTPError as exc:
            return exc.status, exc.headers, exc.read().decode()

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

    def test_railway_binds_all_interfaces_on_port_and_orders_dir(self):
        os.environ["PORT"] = "18080"
        os.environ["SHOP_PORT"] = "9999"
        os.environ.pop("SHOP_HOST", None)
        self.assertEqual(bind_address(), ("0.0.0.0", 18080))
        os.environ.pop("PORT", None)
        self.assertEqual(bind_address(), ("0.0.0.0", 9999))
        volume = self.orders / "volume"
        os.environ["SHOP_ORDERS_DIR"] = str(volume)
        os.environ["SHOP_ORDERS"] = str(self.orders)
        self.assertEqual(_orders_dir(), volume)
        os.environ.pop("SHOP_ORDERS_DIR", None)
        self.assertEqual(_orders_dir(), self.orders)
        server = make_server(0, bind_address()[0], _orders_dir())
        try:
            self.assertEqual(server.server_address[0], "0.0.0.0")
            self.assertEqual(server.orders_dir, self.orders)
        finally:
            server.server_close()

    def _customer(self):
        return {
            "name": "Ada Rogers",
            "email": "ada@example.com",
            "line1": "12 Goondoon Street",
            "suburb": "Gladstone",
            "state": "QLD",
            "postcode": "4680",
        }

    def _place_payid(self, slug="chest-astral-fox-empress", fabric="chest", size="M"):
        os.environ["SHOP_PAYID"] = "0499420228"
        os.environ["SHOP_PAYID_NAME"] = "Rogers Inc Designs"
        return self.post("/api/checkout", {
            "lines": [{"slug": slug, "fabric": fabric, "size": size, "qty": 1}],
            "customer": self._customer(),
        })

    def test_admin_lists_orders_and_mark_paid_creates_a_printful_draft(self):
        from store.admin import admin_token
        from store.printful import _headers

        os.environ["SHOP_ADMIN_PASSWORD"] = "test-admin-secret"
        os.environ["PRINTFUL_API_KEY"] = "printful-test-token"
        os.environ["PRINTFUL_STORE_ID"] = "4242"
        status, login = self.get("/admin")
        self.assertEqual(status, 200)
        self.assertIn("Shop admin", login)
        self.assertIn("noindex", login)
        denied_status, _, denied = self.post_form("/admin/login", {"password": "nope"})
        self.assertEqual(denied_status, 401)
        self.assertIn("not right", denied)
        authed_status, authed_headers, page = self.post_form("/admin/login", {"password": "test-admin-secret"})
        self.assertEqual(authed_status, 200)
        cookie = authed_headers.get("Set-Cookie")
        self.assertIn(admin_token("test-admin-secret"), cookie)
        self.assertIn("No orders yet", page)

        view = self._place_payid()
        self.assertEqual(view["status"], "awaiting_payment")
        self.assertNotIn("printful_order_id", view)
        calls = []

        def fake(env, method, path, payload=None, file=None):
            calls.append({"method": method, "path": path, "payload": payload, "file": file})
            if path == "/files":
                return {"id": 77}
            return {"id": 9001, "status": "draft"}

        with mock.patch("store.printful.read_print_bytes", return_value=b"png-bytes"):
            with mock.patch("store.printful.printful_request", side_effect=fake):
                paid_status, _, paid = self.post_form(
                    f"/admin/orders/{view['id']}/paid",
                    {},
                    cookie=cookie.split(";", 1)[0],
                )
        self.assertEqual(paid_status, 200)
        self.assertIn("9001", paid)
        self.assertIn("draft", paid)
        self.assertEqual(calls[0]["path"], "/files")
        self.assertEqual(calls[0]["file"][1], b"png-bytes")
        self.assertEqual(_headers(os.environ)["X-PF-Store-Id"], "4242")
        self.assertTrue(_headers(os.environ)["Authorization"].startswith("Bearer printful-test-token"))
        created = calls[1]
        self.assertEqual(created["path"], "/orders?confirm=false")
        self.assertEqual(created["payload"]["external_id"], view["id"])
        self.assertEqual(created["payload"]["items"][0]["variant_id"], 4017)
        self.assertEqual(created["payload"]["items"][0]["files"][0]["type"], "front")
        self.assertEqual(created["payload"]["recipient"]["country_code"], "AU")
        self.assertEqual(created["payload"]["recipient"]["state_code"], "QLD")
        saved = json.loads((self.orders / f"{view['id']}.json").read_text(encoding="utf-8"))
        self.assertTrue(saved["payment_taken"])
        self.assertEqual(saved["printful_order_id"], 9001)
        self.assertEqual(saved["printful_status"], "draft")
        self.assertFalse(saved["print_or_ship"])
        buyer = json.loads(self.get(f"/api/orders/{view['id']}")[1])
        self.assertNotIn("printful_order_id", buyer)

        os.environ["PRINTFUL_AUTO_CONFIRM"] = "true"
        second = self._place_payid(slug="starbound-nebula-queen", fabric="poly", size="L")

        def fake_confirm(env, method, path, payload=None, file=None):
            calls.append({"path": path, "payload": payload})
            if path == "/files":
                return {"id": 78}
            return {"id": 9002, "status": "pending"}

        calls.clear()
        with mock.patch("store.printful.read_print_bytes", return_value=b"png"):
            with mock.patch("store.printful.printful_request", side_effect=fake_confirm):
                self.post_form(
                    f"/admin/orders/{second['id']}/paid",
                    {},
                    cookie=cookie.split(";", 1)[0],
                )
        self.assertEqual(calls[1]["path"], "/orders?confirm=true")
        self.assertEqual(calls[1]["payload"]["items"][0]["variant_id"], 8853)
        self.assertEqual(calls[1]["payload"]["items"][0]["files"][0]["type"], "default")
        confirmed = json.loads((self.orders / f"{second['id']}.json").read_text(encoding="utf-8"))
        self.assertEqual(confirmed["printful_order_id"], 9002)
        self.assertTrue(confirmed["print_or_ship"])

    def test_admin_marks_and_deletes_a_test_order(self):
        from store.admin import admin_token

        os.environ["SHOP_ADMIN_PASSWORD"] = "test-admin-secret"
        view = self._place_payid()
        cookie = f"shop_admin={admin_token('test-admin-secret')}"
        denied, _, _ = self.post_form(f"/admin/orders/{view['id']}/delete", {}, cookie="")
        self.assertEqual(denied, 401)
        self.assertTrue((self.orders / f"{view['id']}.json").is_file())
        status, _, page = self.post_form(f"/admin/orders/{view['id']}/test", {}, cookie=cookie)
        self.assertEqual(status, 200)
        self.assertIn("marked as a test order", page)
        saved = json.loads((self.orders / f"{view['id']}.json").read_text(encoding="utf-8"))
        self.assertTrue(saved["test"])
        status, _, page = self.post_form(f"/admin/orders/{view['id']}/delete", {}, cookie=cookie)
        self.assertEqual(status, 200)
        self.assertIn(f"Deleted {view['id']}", page)
        self.assertFalse((self.orders / f"{view['id']}.json").is_file())

    def test_mark_paid_skips_printful_when_the_key_is_missing(self):
        from store.admin import admin_token

        os.environ["SHOP_ADMIN_PASSWORD"] = "test-admin-secret"
        view = self._place_payid(slug="chest-crimson-sun-last-ronin")
        cookie = f"shop_admin={admin_token('test-admin-secret')}"
        with mock.patch("store.printful.printful_request", side_effect=AssertionError("printful called")):
            status, _, page = self.post_form(f"/admin/orders/{view['id']}/paid", {}, cookie=cookie)
        self.assertEqual(status, 200)
        self.assertIn("PRINTFUL_API_KEY is not set", page)
        saved = json.loads((self.orders / f"{view['id']}.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["status"], "paid")
        self.assertEqual(saved["printful_status"], "skipped")
        self.assertNotIn("printful_order_id", saved)

    def test_printful_webhook_records_tracking(self):
        view = self._place_payid()
        path = self.orders / f"{view['id']}.json"
        saved = json.loads(path.read_text(encoding="utf-8"))
        saved["status"] = "paid"
        saved["payment_taken"] = True
        saved["printful_order_id"] = 9001
        path.write_text(json.dumps(saved), encoding="utf-8")
        payload = {
            "type": "package_shipped",
            "data": {
                "order": {"id": 9001, "external_id": view["id"]},
                "shipment": {
                    "carrier": "AUSTRALIA_POST",
                    "tracking_number": "TRACK123",
                    "tracking_url": "https://track.example/TRACK123",
                    "ship_date": "2026-10-14",
                },
            },
        }
        request = urllib.request.Request(
            self.base + "/api/printful/webhook",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request) as response:
            self.assertEqual(response.status, 200)
        updated = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(updated["status"], "shipped")
        self.assertEqual(updated["tracking_number"], "TRACK123")
        self.assertTrue(updated["print_or_ship"])
        buyer = json.loads(self.get(f"/api/orders/{view['id']}")[1])
        self.assertEqual(buyer["tracking_number"], "TRACK123")
        self.assertEqual(buyer["tracking_url"], "https://track.example/TRACK123")
        other = urllib.request.Request(
            self.base + "/api/printful/webhook",
            data=json.dumps({"type": "order_created"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(other) as response:
            self.assertEqual(json.loads(response.read().decode())["ok"], True)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["tracking_number"], "TRACK123")

    def test_payid_order_emails_and_skips_when_smtp_is_unset(self):
        from store.mail import alert_email

        self.assertEqual(alert_email(), "rogersinc426@gmail.com")
        view = self._place_payid()
        self.assertTrue((self.orders / f"{view['id']}.json").is_file())

        os.environ["SMTP_HOST"] = "smtp.test"
        os.environ["SMTP_PORT"] = "587"
        os.environ["SMTP_USER"] = "rogersinc426@gmail.com"
        os.environ["SMTP_PASS"] = "fake-app-password"
        os.environ["SMTP_FROM"] = "rogersinc426@gmail.com"
        os.environ["SHOP_ALERT_EMAIL"] = "jason@example.com"

        class FakeSMTP:
            opened = []

            def __init__(self, host, port, timeout=None):
                self.host = host
                self.port = port
                self.timeout = timeout
                self.messages = []
                self.user = ""
                FakeSMTP.opened.append(self)

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def ehlo(self):
                return None

            def starttls(self, context=None):
                return None

            def login(self, user, password):
                self.user = user
                self.password = password

            def send_message(self, message):
                self.messages.append(message)

        from store.mail import wait_for_mail

        with mock.patch("store.mail.smtplib.SMTP", FakeSMTP):
            mailed = self._place_payid()
            wait_for_mail()
        messages = [item for smtp in FakeSMTP.opened for item in smtp.messages]
        self.assertEqual(FakeSMTP.opened[0].timeout, 8)
        self.assertEqual(len(messages), 2)
        self.assertEqual(FakeSMTP.opened[0].host, "smtp.test")
        self.assertEqual(FakeSMTP.opened[0].password, "fake-app-password")
        alert = next(item for item in messages if item["To"] == "jason@example.com")
        customer = next(item for item in messages if item["To"] == "ada@example.com")
        self.assertIn(mailed["id"], alert["Subject"])
        self.assertIn("0499420228", customer.get_content())
        self.assertIn(mailed["id"], customer.get_content())
        self.assertIn("Rogers Inc Designs", customer.get_content())
        self.assertEqual(customer["From"], "rogersinc426@gmail.com")

        class BoomSMTP(FakeSMTP):
            def login(self, user, password):
                raise OSError("smtp down")

        with mock.patch("store.mail.smtplib.SMTP", BoomSMTP):
            still = self._place_payid(slug="void-king")
            wait_for_mail()
        self.assertEqual(still["status"], "awaiting_payment")
        self.assertTrue((self.orders / f"{still['id']}.json").is_file())

        shipped = json.loads((self.orders / f"{mailed['id']}.json").read_text(encoding="utf-8"))
        shipped["status"] = "paid"
        shipped["printful_order_id"] = 44
        (self.orders / f"{mailed['id']}.json").write_text(json.dumps(shipped), encoding="utf-8")
        payload = {
            "type": "package_shipped",
            "data": {
                "order": {"external_id": mailed["id"]},
                "shipment": {
                    "carrier": "AUSTRALIA_POST",
                    "tracking_number": "SHIP999",
                    "tracking_url": "https://track.example/SHIP999",
                },
            },
        }
        FakeSMTP.opened = []
        with mock.patch("store.mail.smtplib.SMTP", FakeSMTP):
            self.post("/api/printful/webhook", payload)
            self.post("/api/printful/webhook", payload)
            wait_for_mail()
        shipped_messages = [item for smtp in FakeSMTP.opened for item in smtp.messages]
        self.assertEqual(len(shipped_messages), 1)
        self.assertIn("has shipped", shipped_messages[0]["Subject"])
        self.assertIn("SHIP999", shipped_messages[0].get_content())
        self.assertIn("https://track.example/SHIP999", shipped_messages[0].get_content())


    def test_stripe_webhook_marks_the_order_paid_and_creates_printful(self):
        import hashlib
        import hmac
        import time

        os.environ["STRIPE_SECRET_KEY"] = "sk_test_example"
        os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test"
        os.environ["PRINTFUL_API_KEY"] = "printful-test-token"

        def fake_stripe(path, secret, fields=None):
            return {"id": "cs_test_hook", "url": "https://checkout.stripe.com/c/pay/cs_test_hook"}

        with mock.patch("store.checkout._stripe_request", side_effect=fake_stripe):
            view = self.post("/api/checkout", {
                "payment": "card",
                "lines": [{"slug": "starbound-nebula-queen", "fabric": "poly", "size": "M", "qty": 1}],
                "customer": self._customer(),
            })
        self.assertEqual(view["status"], "pending_payment")
        self.assertEqual(view["total_cents"], 6500)
        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_hook",
                    "payment_status": "paid",
                    "amount_total": 6500,
                    "currency": "aud",
                    "client_reference_id": view["id"],
                    "metadata": {"order_id": view["id"]},
                    "total_details": {"amount_shipping": 0},
                    "shipping_details": {"address": {"country": "AU"}},
                }
            },
        }
        raw = json.dumps(event).encode()
        stamp = int(time.time())
        signature = hmac.new(b"whsec_test", f"{stamp}.".encode() + raw, hashlib.sha256).hexdigest()
        header = f"t={stamp},v1={signature}"
        calls = []

        def fake_printful(env, method, path, payload=None, file=None):
            calls.append(path)
            if path == "/files":
                return {"id": 11}
            self.assertEqual(payload["recipient"]["country_code"], "AU")
            self.assertEqual(payload["shipping"], "STANDARD")
            return {"id": 55, "status": "draft"}

        with mock.patch("store.printful.read_print_bytes", return_value=b"png"):
            with mock.patch("store.printful.printful_request", side_effect=fake_printful):
                status, body = self.post_signed("/api/stripe/webhook", raw, header)
        self.assertEqual(status, 200)
        self.assertEqual(calls[1], "/orders?confirm=false")
        saved = json.loads((self.orders / f"{view['id']}.json").read_text(encoding="utf-8"))
        self.assertTrue(saved["payment_taken"])
        self.assertEqual(saved["status"], "paid")
        self.assertEqual(saved["printful_order_id"], 55)
        self.assertIn(view["id"], body)

        status, _ = self.post_signed("/api/stripe/webhook", raw, "t=1,v1=deadbeef")
        self.assertEqual(status, 400)
        os.environ.pop("STRIPE_WEBHOOK_SECRET", None)
        status, denied = self.post_signed("/api/stripe/webhook", raw, header)
        self.assertEqual(status, 503)
        self.assertIn("not set", denied)
        self.assertEqual(json.loads((self.orders / f"{view['id']}.json").read_text(encoding="utf-8"))["printful_order_id"], 55)

    def post_signed(self, path, raw, signature):
        request = urllib.request.Request(
            self.base + path,
            data=raw,
            headers={"Content-Type": "application/json", "Stripe-Signature": signature},
        )
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, response.read().decode()
        except urllib.error.HTTPError as exc:
            return exc.status, exc.read().decode()


class PrintfulMapTests(unittest.TestCase):
    def test_variant_map_matches_the_printful_catalog(self):
        from store.printful import placement_for, shirt_color, variant_id

        catalog = load_catalog()
        fox = next(item for item in catalog["products"] if item["slug"] == "chest-astral-fox-empress")
        fuel = next(item for item in catalog["products"] if item["slug"] == "as-high-as-fuel")
        nebula = next(item for item in catalog["products"] if item["slug"] == "starbound-nebula-queen")
        self.assertEqual(shirt_color(fox), "black")
        self.assertEqual(shirt_color(fuel), "white")
        self.assertEqual(variant_id(catalog, fox, "chest", "M"), 4017)
        self.assertEqual(variant_id(catalog, fox, "chest", "3XL"), 5295)
        self.assertEqual(variant_id(catalog, fuel, "chest", "M"), 4012)
        self.assertEqual(variant_id(catalog, nebula, "poly", "XS"), 8850)
        self.assertEqual(variant_id(catalog, nebula, "cotton", "2XL"), 33942)
        self.assertEqual(placement_for(catalog, "poly"), "default")
        self.assertEqual(placement_for(catalog, "cotton"), "front_dtfabric")
        self.assertEqual(placement_for(catalog, "chest"), "front")
        public = json.dumps(public_catalog(checkout_public()))
        self.assertNotIn("printful_variants", public)
        self.assertNotIn("8852", public)


if __name__ == "__main__":
    unittest.main()
