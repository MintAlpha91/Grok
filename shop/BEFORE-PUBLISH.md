# Before this shop goes live

The website brand is Rogers Inc / Rogers Inc Designs. Elemental Wood is the Etsy shop name only.

Jason still needs to confirm these. They are not invented on the site.

- Contact email for damaged or misprinted orders. None is set. The shipping page says the address is not published yet.
- Remake window. Marketing’s draft says email within 7 days of delivery. That number is not confirmed.

Also still open:

- This server stores the order. It does not send the “we’ll email when it ships” message itself.
- Shirt photos are the Printful mockups in `public/mockups/{slug}-aop-poly.jpg` and `{slug}-aop-cotton.jpg`, cropped to 1280×720 so the caption strip is gone. The page price is the only price. Do not put the Printful caption (old AU$69 / AU$75) back on the photo. Pin crops for six designs are in the same folder and are not gallery tiles.
- Scene sentences live on each product in `catalog.json`. They were carried from the Etsy listing pack into Marketing’s blurb template. Marketing can replace `products.*.scene`.
- The live collection nav label is Full Bleed. Blackletter, As High As Fuel, Brush & Smoke, Living Screens, and Night Shift are upcoming collection pages. “As High As Fuel” is the stoner lane, not a priced product. Night Shift is seasonal, not an adults-only lane.
- Remove `<meta name="robots" content="noindex">` when Jason says the shop should be indexed. Test-mode Stripe still keeps the shop out of search.
- Stripe is test mode only. Set `STRIPE_SECRET_KEY` to `sk_test_…` and `SHOP_BASE_URL` to the public origin. Optional `STRIPE_PUBLISHABLE_KEY` (`pk_test_…`) is unused by hosted Checkout. Do not commit keys. The server rejects `sk_live_` / `rk_live_`. See README “Payments” for the test card.
- Free shipping on the Stripe session is Australia only. Do not add a zero shipping rate for other countries. Overseas postage stays closed until a charged rate is set.
- PayID (`SHOP_PAYID`) is the fallback when the Stripe secret is unset. It does not run alongside Stripe.

Demo checkout, used when Stripe and PayID are both unset, does not charge a card and does not send anything to print. A Stripe test payment is a real test-mode charge and still does not send the shirt to print by itself.
