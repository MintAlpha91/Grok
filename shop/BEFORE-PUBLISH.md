# Before this shop goes live

This shop is a preview catalog, not a live store. Do not treat it as go-live ready until every collection has at least 10 items. A thin collection stays `upcoming` or `ready` (ready to list). It is not the public storefront. When Design supplies more art and mockups, add them to the catalog and move the lane toward that floor. Do not deploy, and do not describe the site as open.

The website brand is Rogers Inc / Rogers Inc Designs. Elemental Wood is the Etsy shop name only.

Jason still needs to confirm these. They are not invented on the site.

- Contact email for damaged or misprinted orders. None is set. The shipping page says the address is not published yet.
- Remake window. Marketing’s draft says email within 7 days of delivery. That number is not confirmed.

Also still open:

- This server stores the order. It does not send the “we’ll email when it ships” message itself.
- Shirt photos are the Printful mockups in `public/mockups/{slug}-aop-poly.jpg` and `{slug}-aop-cotton.jpg`, cropped to 1280×720 so the caption strip is gone. The page price is the only price. Do not put the Printful caption (old AU$69 / AU$75) back on the photo. Pin crops for six designs are in the same folder and are not gallery tiles.
- Scene sentences live on each product in `catalog.json`. They were carried from the Etsy listing pack into Marketing’s blurb template. Marketing can replace `products.*.scene`.
- Live poly full bleed is the seven aligned core scenes plus Nine-Tail Neon Shrine. The other new-concept all-over tees are upcoming, not live. Nebula Queen full bleed stays held until alignment is confirmed. The chest print of that scene stays with the other seven chest tees.
- Blackletter is a preview lane, 10 cards, at AU$47. Those cards can be ordered in the demo shop and stay held for a real go-live until Jason clears them. As High As Fuel is one upcoming design, not a storefront: As High As The Price Of Fuel (Etsy 4590224889), white and heather. The other Fuel art stays out of the public count until Design supplies more. Brush & Smoke and Biomechanical stay off sale.
- Full Bleed and Chest print are ready to list, at 8 designs each. Living Screens uses the wallpaper blurb and stays upcoming: Crimson Sun and Quiet Rain packs are noted as 10 ready, but no wallpaper files are on this site, so nothing in that lane can be downloaded. Night Shift is seasonal, not an adults-only lane. Blackletter and As High As Fuel marketing blurbs stay off the public shop. The site stays a preview until every collection that would be live has at least 10 items. Fuel is not one of those.
- Remove `<meta name="robots" content="noindex">` when Jason says the shop should be indexed. Test-mode Stripe still keeps the shop out of search.
- Stripe Checkout is ready and parked. Leave `STRIPE_SECRET_KEY` unset. Use `SHOP_PAYID` or `SHOP_CHECKOUT=demo` until Jason adds `sk_test_` later. Do not commit keys. The server rejects `sk_live_` / `rk_live_`. See README “Payments”.
- Free shipping on the Stripe session is Australia only. Do not add a zero shipping rate for other countries. Overseas postage stays closed until a charged rate is set.
- PayID (`SHOP_PAYID`) is the path when the Stripe secret is unset. It does not run alongside Stripe.

Demo checkout, used when Stripe and PayID are both unset, does not charge a card and does not send anything to print. A Stripe test payment is a real test-mode charge and still does not send the shirt to print by itself.
