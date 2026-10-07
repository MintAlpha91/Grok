# Rogers Inc Designs shop

Draft storefront for Rogers Inc Designs. The first live lane is the all-over print wave. Later lanes (gothic blackletter, stoner, calligraphy, and anything after that) are collections in the catalog, not extra pages. The header uses `public/brand/logo.png`, the homepage hero uses `public/brand/banner.png`, and the strip under the nav uses `public/brand/mini-banner.png`. **Elemental Wood** is the Etsy shop name only, linked from the footer and the about page.

Prices are GST-inclusive official-store prices, under the Etsy ladder: polyester AU$65 (2XL +AU$4), cotton AU$71 (opens after the first sales), chest print AU$47 (2XL +AU$4, 3XL +AU$7, no 4XL or 5XL). The site does not show the Etsy amount on the same tee. The line is “Official store — no Etsy fees.” Free shipping is Australia only. Overseas postage is charged and is not open, so checkout does not give it away. GST is one eleventh of the price already shown. Checkout does not add GST again. Page wording lives in `web-copy.json`. Products, collections, and series live in `catalog.json`. The homepage, shop, and `/collection/…` pages render that list. Adding a tee does not need a new page.

## Add a product or a lane

1. Add an object to `products` in `catalog.json`: `slug`, `name`, `listing_name`, `collection`, `series`, `series_name`, `status` (`live` or `upcoming`), `tags`, `hook`, and `scene`. Omit `fabrics` to use the all-over print fabrics. Only a fabric with `status` `live` can be ordered. Set `fabrics` to `["chest"]` for a chest-print collector tee. A product with `status` other than `live` stays out of the shop and cannot be ordered. Matching wallpapers are the `wallpaper-bundle` add-on at AU$10 with a tee; leave `status` as `held` until the files exist.
2. Drop mockups at `public/mockups/{slug}-aop-poly.jpg` and `public/mockups/{slug}-aop-cotton.jpg` (or `{slug}-poly.jpg` / `{slug}-cotton.jpg` for a later lane). The fabric selector uses whichever file exists.
3. To open a new lane, add a collection (`id`, `name`, `label`, `status`, optional `intro`, `detail`, `example`). The homepage lane row and the shop filters pick it up. Series labels go in the `series` list; the shop only shows a series chip once a live product uses it.

The Full Bleed intro is the `aop` collection text in `catalog.json`. It says first wave, not a fixed shirt count. “As High As Fuel” is the stoner collection’s example line, not a priced product. The shop copy for “New drops” and “More designs coming.” lives in `web-copy.json`.

Demo checkout does not charge a card and does not print or ship a shirt.

## Run

```bash
cd shop
SHOP_CHECKOUT=demo PYTHONPATH=src python3 -m store
```

Open http://127.0.0.1:8765

## Payments

Stripe Checkout is the card path. PayID is only used when no Stripe secret is set. Demo runs when `SHOP_CHECKOUT=demo` and neither of those is set. With none of them set, checkout refuses the order.

Use Stripe **test** keys only. The server rejects `sk_live_` and `rk_live_`. Do not commit keys. Copy `.env.example` to `.env` (gitignored) or export the variables in the shell.

| Variable | Required | What to set |
| --- | --- | --- |
| `STRIPE_SECRET_KEY` | Yes, for card checkout | `sk_test_…` from the Stripe Dashboard, test mode |
| `STRIPE_PUBLISHABLE_KEY` | No | `pk_test_…` if you add Stripe.js later. Hosted Checkout does not read it |
| `SHOP_BASE_URL` | Yes, once the site has a public origin | Return origin Stripe sends the buyer back to, no trailing path. Local: `http://127.0.0.1:8765` |
| `SHOP_PAYID` | No | PayID address. Ignored while `STRIPE_SECRET_KEY` is set |
| `SHOP_PAYID_NAME` | No | Defaults to Rogers Inc Designs |
| `SHOP_CHECKOUT` | No | `demo` for a no-charge walkthrough when Stripe is unset |

```bash
cd shop
export STRIPE_SECRET_KEY=sk_test_...
export SHOP_BASE_URL=http://127.0.0.1:8765
PYTHONPATH=src python3 -m store
```

Card checkout creates a Stripe Checkout Session in AUD. Each line is the catalog price (name, fabric, size). GST is already inside that amount: `automatic_tax` is off and each price is `tax_behavior=inclusive`. The only shipping rate is free delivery inside Australia. Other countries are not offered a free rate, and overseas checkout stays closed until a charged rate is added. Success returns to `/order/RID-…?session_id={CHECKOUT_SESSION_ID}`. Cancel returns to `/checkout?cancelled=1`.

Test a card in the Stripe Dashboard’s test mode with `4242 4242 4242 4242`, any future expiry, any CVC, and any postcode. The order stays unpaid until Stripe reports `payment_status=paid` for that session and the paid total matches the catalog total. A paid order is saved for a person to send to Printful. Nothing is pushed to Printful automatically, and a test payment does not print a shirt by itself.

PayID, only when Stripe is unset:

```bash
SHOP_PAYID=you@bank SHOP_PAYID_NAME="Rogers Inc Designs" PYTHONPATH=src python3 -m store
```

## Tests

```bash
cd shop
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Before publish

See `BEFORE-PUBLISH.md`. Contact email and the remake window are still for Jason to confirm.
