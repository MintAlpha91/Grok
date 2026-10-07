# Rogers Inc Designs shop

Draft preview catalog for Rogers Inc Designs. This is not a live store. A collection is not the public storefront until it has at least 10 items, and the site stays a preview until every collection meets that floor. Thin lanes use `ready` (ready to list) or `upcoming`. Later lanes (gothic blackletter, fuel, calligraphy, and anything after that) are collections in the catalog, not extra pages. The header uses `public/brand/logo.png`, the homepage hero uses `public/brand/banner.png`, and the strip under the nav uses `public/brand/mini-banner.png`. **Elemental Wood** is the Etsy shop name only, linked from the footer and the about page.

Prices are GST-inclusive official-store prices, under the Etsy ladder: polyester AU$65 (2XL +AU$4), cotton AU$71 (opens after the first sales), chest print AU$47 (2XL +AU$4, 3XL +AU$7, no 4XL or 5XL). The site does not show the Etsy amount on the same tee. The line is “Official store — no Etsy fees.” Free shipping is Australia only. Overseas postage is charged and is not open, so checkout does not give it away. GST is one eleventh of the price already shown. Checkout does not add GST again. Page wording lives in `web-copy.json`. Products, collections, and series live in `catalog.json`. The homepage, shop, and `/collection/…` pages render that list. Adding a tee does not need a new page.

## Add a product or a lane

1. Add an object to `products` in `catalog.json`: `slug`, `name`, `listing_name`, `collection`, `series`, `series_name`, `status` (`live`, `preview`, `upcoming`, or `held`), `tags`, `hook`, and `scene`. Omit `fabrics` to use the all-over print fabrics. Only a fabric with `status` `live` can be ordered. Set `fabrics` to `["chest"]` for a chest-print collector tee. `live` and `preview` show in this demo catalog. `preview` can be ordered here and stays held for a real go-live. `upcoming` and `held` stay out of the shop and cannot be ordered. Matching wallpapers with a tee stay the `wallpaper-bundle` add-on at AU$10, still held. Wallpaper pack cards use the `wallpaper` fabric at AU$12, the pack price from pack.json.
2. Drop mockups at `public/mockups/{slug}-aop-poly.jpg` and `public/mockups/{slug}-aop-cotton.jpg` (or `{slug}-poly.jpg` / `{slug}-cotton.jpg` for a later lane). The fabric selector uses whichever file exists. Chest print files for Printful go in `print-ready/gothic/` or `print-ready/fuel/` as `Rogers-Inc-Designs-{slug}-front-4500x5400.png` and are recorded on the product as `print_ready`. Those files stay out of `public/`. Fuel print files are white-background RGB for white and heather shirts only.
3. To open a new lane, add a collection (`id`, `name`, `label`, `status`, optional `intro`, `detail`, `example`). Use `upcoming` while the lane is empty and `ready` while it has designs but fewer than 10. Do not set `status` to `live` on a thin lane. The public catalog rewrites a `live` lane under 10 items to `ready`. The homepage lane row and the shop filters pick it up. Series labels go in the `series` list; the shop only shows a series chip once a visible product uses it.

The Full Bleed intro is the `aop` collection text in `catalog.json`. It does not name a fixed shirt count. Full Bleed, Gothic, and As High As Fuel are live once each lane has at least 10 shop cards. Nebula Queen stays held. The shop copy for “New drops” and “More designs coming.” lives in `web-copy.json`.

Demo checkout does not charge a card and does not print or ship a shirt.

## Run

Leave `STRIPE_SECRET_KEY` unset. Stripe Checkout is in the repo and parked until Jason adds `sk_test_` later. Local checkout is demo or PayID.

```bash
cd shop
SHOP_CHECKOUT=demo PYTHONPATH=src python3 -m store
```

Open http://127.0.0.1:8765

PayID instead of demo:

```bash
cd shop
SHOP_PAYID=you@bank SHOP_PAYID_NAME="Rogers Inc Designs" PYTHONPATH=src python3 -m store
```

## Payments

Stripe Checkout is ready and parked. The server uses it only when `STRIPE_SECRET_KEY` is set. With that variable unset, `SHOP_PAYID` shows PayID and holds the order unpaid. If PayID is also unset, `SHOP_CHECKOUT=demo` walks through checkout with no charge and no print. If none of those are set, checkout refuses the order.

Do not commit keys. The server rejects `sk_live_` and `rk_live_`. Copy `.env.example` to `.env` (gitignored) only if you want those variables in one file. The process does not load `.env` by itself.

| Variable | When |
| --- | --- |
| `SHOP_CHECKOUT=demo` | Local no-charge walkthrough. Use this until a PayID or a Stripe test key is set |
| `SHOP_PAYID` | PayID address. Used when `STRIPE_SECRET_KEY` is unset |
| `SHOP_PAYID_NAME` | Optional. Defaults to Rogers Inc Designs |
| `STRIPE_SECRET_KEY` | Later. `sk_test_…` turns hosted Checkout on |
| `STRIPE_PUBLISHABLE_KEY` | Later, optional. `pk_test_…`. Hosted Checkout does not read it |
| `SHOP_BASE_URL` | Later, with Stripe. Return origin, no path. Local: `http://127.0.0.1:8765` |

When Jason sets `sk_test_…`, card checkout creates a Stripe Checkout Session in AUD at the catalog price (name, fabric, size). GST is already inside that amount: `automatic_tax` is off and each price is `tax_behavior=inclusive`. The only shipping rate is free delivery inside Australia. Success returns to `/order/RID-…?session_id={CHECKOUT_SESSION_ID}`. Cancel returns to `/checkout?cancelled=1`. Test card `4242 4242 4242 4242`, any future expiry, any CVC. A paid order is saved for a person to send to Printful. Nothing is pushed to Printful automatically.

## Tests

```bash
cd shop
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Before publish

See `BEFORE-PUBLISH.md`. Contact email and the remake window are still for Jason to confirm.
