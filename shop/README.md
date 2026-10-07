# Rogers Inc Designs shop

Draft storefront for the eight all-over print tees. The site brand is **Rogers Inc** / **Rogers Inc Designs**. The header uses `public/brand/logo.png`, the homepage hero uses `public/brand/banner.png`, and the strip under the nav uses `public/brand/mini-banner.png`. **Elemental Wood** is the Etsy shop name only, linked from the footer and the about page.

Prices are locked: polyester AU$69 (2XL AU$73), cotton AU$75 (2XL AU$79). Free shipping in Australia. Sizes XS–2XL. Buyer-facing wording lives in `web-copy.json`.

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
