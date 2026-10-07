# Before this shop goes live

The website brand is Rogers Inc / Rogers Inc Designs. Elemental Wood is the Etsy shop name only.

Jason still needs to confirm these. They are not invented on the site.

- Contact email for damaged or misprinted orders. None is set. The shipping page says the address is not published yet.
- Remake window. Marketing’s draft says email within 7 days of delivery. That number is not confirmed.

Also still open:

- This server stores the order. It does not send the “we’ll email when it ships” message itself.
- Shirt photos are the Printful mockups in `public/mockups/{slug}-aop-poly.jpg` and `{slug}-aop-cotton.jpg`, cropped to 1280×720 so the caption strip is gone. The page price is the only price. Do not put the Printful caption (old AU$69 / AU$75) back on the photo. Pin crops for six designs are in the same folder and are not gallery tiles.
- Scene sentences live on each product in `catalog.json`. They were carried from the Etsy listing pack into Marketing’s blurb template. Marketing can replace `products.*.scene`.
- Live lanes are Full Bleed and Chest print. Full Bleed is the seven aligned core scenes plus the 14 new-concept tees. Nebula Queen full bleed is held until the alignment is confirmed. The chest print of that scene stays with the other seven chest tees. As High As Fuel is a hard hold: the collection is hidden from the shop until mockups show the art, and only white and heather when that happens. Blackletter, Brush & Smoke, and Biomechanical stay off sale until Jason greenlights them. Living Screens and Night Shift are still upcoming. Night Shift is seasonal, not an adults-only lane.
- Remove `<meta name="robots" content="noindex">` when Jason says the shop should be indexed. Test-mode Stripe still keeps the shop out of search.
- Stripe Checkout is ready and parked. Leave `STRIPE_SECRET_KEY` unset. Use `SHOP_PAYID` or `SHOP_CHECKOUT=demo` until Jason adds `sk_test_` later. Do not commit keys. The server rejects `sk_live_` / `rk_live_`. See README “Payments”.
- Free shipping on the Stripe session is Australia only. Do not add a zero shipping rate for other countries. Overseas postage stays closed until a charged rate is set.
- PayID (`SHOP_PAYID`) is the path when the Stripe secret is unset. It does not run alongside Stripe.

Demo checkout, used when Stripe and PayID are both unset, does not charge a card and does not send anything to print. A Stripe test payment is a real test-mode charge and still does not send the shirt to print by itself.
