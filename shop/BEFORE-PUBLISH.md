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
- Design’s named collections are ready at 10 or more for the preview catalog. Gothic is 10 preview cards and Fuel is 10 preview cards. Neither is featured until Jason clears it. As High As The Price Of Fuel shows white and heather only. The site is still not a public go-live.
- Crimson Sun Last Ronin is featured again because the mockup is wired. Quiet Rain Umbrella Crossing and Window Seat are featured. Four Quiet Rain fills are in the catalog as upcoming, not on the shop: Ramen Steam Alley, Bus Stop Downpour, Vending Glow Puddle, Quiet Lantern Bridge. They are print-ready and the mockups are not on this site. Nebula Queen full bleed stays a preview card.
- Blackletter is 10 preview cards from the gothic fill. As High As Fuel is 10 preview cards from the fuel fill. The main Fuel tee uses the white and heather photos only. Brush & Smoke is 4 preview cards. Biomechanical is the Half Machine Skull preview card.
- Wave-1 prices are locked if those products are added later: hoodie AU$75, AOP beanie AU$49, Flexfit AU$55. No mockups for them are on this site, so they are not in the catalog.
- Full Bleed is ready to list at 22 designs and is still not the open store. Chest print is ready to list at 8. Living Screens uses the wallpaper blurb and stays upcoming: Design counts 57 ready packs, but the files are not on this site, so nothing in that lane can be downloaded. Night Shift is seasonal, not an adults-only lane. Blackletter and As High As Fuel marketing blurbs stay off the public shop. The site stays a preview until Jason clears Gothic and Fuel. Those lanes are preview cards, not featured.
- Remove `<meta name="robots" content="noindex">` when Jason says the shop should be indexed. Test-mode Stripe still keeps the shop out of search.
- Stripe Checkout is ready and parked. Leave `STRIPE_SECRET_KEY` unset. Use `SHOP_PAYID` or `SHOP_CHECKOUT=demo` until Jason adds `sk_test_` later. Do not commit keys. The server rejects `sk_live_` / `rk_live_`. See README “Payments”.
- Free shipping on the Stripe session is Australia only. Do not add a zero shipping rate for other countries. Overseas postage stays closed until a charged rate is set.
- PayID (`SHOP_PAYID`) is the path when the Stripe secret is unset. It does not run alongside Stripe.

Demo checkout, used when Stripe and PayID are both unset, does not charge a card and does not send anything to print. A Stripe test payment is a real test-mode charge and still does not send the shirt to print by itself.
