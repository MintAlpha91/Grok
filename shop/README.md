# Rogers Inc Designs shop

Draft storefront for Rogers Inc Designs. The first live lane is the all-over print wave. Later lanes (gothic blackletter, stoner, calligraphy, and anything after that) are collections in the catalog, not extra pages. The header uses `public/brand/logo.png`, the homepage hero uses `public/brand/banner.png`, and the strip under the nav uses `public/brand/mini-banner.png`. **Elemental Wood** is the Etsy shop name only, linked from the footer and the about page.

Prices are GST-inclusive official-store prices, under the Etsy ladder: polyester AU$65 (2XL +AU$4), cotton AU$71 (opens after the first sales), chest print AU$47 (2XL +AU$4, 3XL +AU$7, no 4XL or 5XL). The site does not show the Etsy amount on the same tee. The line is “Official store — no Etsy fees.” Free shipping is Australia only. Overseas postage is charged and is not open, so checkout does not give it away. GST is one eleventh of the price already shown. Checkout does not add GST again. Page wording lives in `web-copy.json`. Products, collections, and series live in `catalog.json`. The homepage, shop, and `/collection/…` pages render that list. Adding a tee does not need a new page.

## Add a product or a lane

1. Add an object to `products` in `catalog.json`: `slug`, `name`, `listing_name`, `collection`, `series`, `series_name`, `status` (`live` or `upcoming`), `tags`, `hook`, and `scene`. Omit `fabrics` to use the all-over print fabrics. Only a fabric with `status` `live` can be ordered. Set `fabrics` to `["chest"]` for a chest-print collector tee. A product with `status` other than `live` stays out of the shop and cannot be ordered. Matching wallpapers are the `wallpaper-bundle` add-on at AU$10 with a tee; leave `status` as `held` until the files exist.
2. Drop mockups at `public/mockups/{slug}-aop-poly.jpg` and `public/mockups/{slug}-aop-cotton.jpg` (or `{slug}-poly.jpg` / `{slug}-cotton.jpg` for a later lane). The fabric selector uses whichever file exists.
3. To open a new lane, add a collection (`id`, `name`, `label`, `status`, optional `intro`, `detail`, `example`). The homepage lane row and the shop filters pick it up. Series labels go in the `series` list; the shop only shows a series chip once a live product uses it.

The AOP intro “Eight designs…” is the `aop` collection text in `catalog.json`. Change that sentence there when the wave grows. “As High As Fuel” is the stoner collection’s example line, not a priced product.

Demo checkout does not charge a card and does not print or ship a shirt.

## Run

```bash
cd shop
SHOP_CHECKOUT=demo PYTHONPATH=src python3 -m store
```

Open http://127.0.0.1:8765

## Payments

Stripe is used when `STRIPE_SECRET_KEY` is set. Otherwise PayID is used when `SHOP_PAYID` is set. Otherwise demo mode runs when `SHOP_CHECKOUT=demo`. With none of those set, checkout refuses the order.

```bash
STRIPE_SECRET_KEY=sk_live_... SHOP_BASE_URL=https://your-domain PYTHONPATH=src python3 -m store
SHOP_PAYID=you@bank SHOP_PAYID_NAME="Rogers Inc Designs" PYTHONPATH=src python3 -m store
```

Paid orders are saved for a person to send to Printful. Nothing is pushed to Printful automatically.

## Tests

```bash
cd shop
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Before publish

See `BEFORE-PUBLISH.md`. Contact email and the remake window are still for Jason to confirm.
