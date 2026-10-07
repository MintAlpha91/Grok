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
    load_catalog,
    load_copy,
    public_catalog,
    quote_lines,
    settle,
    validate_customer,
)
from store.checkout import checkout_mode, checkout_public, place_order, stripe_fields  # noqa: E402
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
        live = [item for item in catalog["products"] if item.get("status", "live") == "live"]
        self.assertEqual(len(public["products"]), 8)
        self.assertEqual(len(live), 8)
        for design in public["products"]:
            self.assertEqual([item["id"] for item in design["fabrics"]], ["poly"])
            self.assertEqual([item["id"] for item in design["held_fabrics"]], ["cotton"])
            self.assertEqual(design["held_fabrics"][0]["price_cents"], 7100)
            url = design["fabrics"][0]["mockup"]
            self.assertEqual(url, f"/mockups/{design['slug']}-aop-poly.jpg")
            self.assertTrue((ROOT / "public" / url.lstrip("/")).is_file())
            cotton = ROOT / "public" / "mockups" / f"{design['slug']}-aop-cotton.jpg"
            self.assertTrue(cotton.is_file())
            self.assertEqual(design["image"], url)

    def test_lanes_are_data_not_a_fixed_page(self):
        public = public_catalog(checkout_public())
        ids = [item["id"] for item in public["collections"]]
        self.assertEqual(ids, ["aop", "chest-dtg", "gothic-blackletter", "stoner", "calligraphy", "living-screens", "night-shift"])
        aop = next(item for item in public["collections"] if item["id"] == "aop")
        stoner = next(item for item in public["collections"] if item["id"] == "stoner")
        self.assertEqual(aop["count"], 8)
        self.assertEqual(aop["status"], "live")
        self.assertEqual(stoner["count"], 0)
        self.assertEqual(stoner["status"], "upcoming")
        self.assertEqual(stoner["example"], "As High As Fuel")
        self.assertEqual(stoner["landing"], "as-high-as-fuel")
        gothic = next(item for item in public["collections"] if item["id"] == "gothic-blackletter")
        self.assertEqual(gothic["landing"], "blackletter")
        self.assertEqual(gothic["label"], "Blackletter")
        self.assertEqual(next(item["label"] for item in public["collections"] if item["id"] == "aop"), "Full Bleed")
        self.assertEqual(next(item["label"] for item in public["collections"] if item["id"] == "calligraphy"), "Brush & Smoke")
        self.assertEqual(stoner["sub"], "slow burns & night drives")
        self.assertEqual(
            [item["label"] for item in public["series"]],
            ["Ronin Rain", "Quiet Rain", "Starbound", "Crimson Sun", "Crimson Oni", "Neon Cyberpunk"],
        )
        script = (ROOT / "public" / "js" / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "public" / "index.html").read_text(encoding="utf-8")
        self.assertIn("catalog.products", script)
        self.assertIn("catalog.collections", script)
        self.assertIn("/collection/", script)
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
        public_body = json.dumps(public_catalog(checkout_public()))
        self.assertNotIn("etsy_cents", public_body)
        self.assertIn("Official store", public_body)
        chest = catalog["fabrics"]["chest"]
        self.assertEqual(chest["status"], "lane")
        self.assertNotIn("4XL", chest["sizes"])
        self.assertNotIn("5XL", chest["sizes"])
        public = public_catalog(checkout_public())
        self.assertEqual(public["offer"]["hero_fabric"], "poly")
        self.assertEqual(public["addons"][0]["with_shirt_cents"], 1000)
        self.assertEqual(public["addons"][0]["status"], "held")
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
        self.assertIn("Crimson Sun: The Last Ronin", fields["line_items[0][price_data][product_data][name]"])


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
        self.assertEqual(len(catalog["products"]), 8)
        self.assertIn("gothic-blackletter", [item["id"] for item in catalog["collections"]])
        self.assertIn("as-high-as-fuel", [item["landing"] for item in catalog["collections"]])
        self.assertEqual(catalog["products"][0]["fabrics"][0]["id"], "poly")
        self.assertEqual(catalog["products"][0]["held_fabrics"][0]["id"], "cotton")
        self.assertIn("no shirt will be printed", catalog["checkout"]["demo_lead"])
        view = self.post("/api/checkout", {
            "lines": [{"slug": "starbound-nebula-queen", "fabric": "poly", "size": "XS", "qty": 1}],
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
