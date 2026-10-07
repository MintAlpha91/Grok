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
- Jason cleared Gothic and As High As Fuel. Both lanes are live on the catalog, 10 cards each. As High As The Price Of Fuel shows white and heather only. Colour shots stay off the shop. The site is still demo checkout, not a deployed store.
- Crimson Sun Last Ronin is featured because the mockup is wired. Quiet Rain Umbrella Crossing and Window Seat are featured. Four Quiet Rain fills are in the catalog as upcoming, not on the shop: Ramen Steam Alley, Bus Stop Downpour, Vending Glow Puddle, Quiet Lantern Bridge. They are print-ready and the mockups are not on this site. Nebula Queen is held off the shop, including New drops and the chest lane, until Design clears the alignment.
- Blackletter is 10 live cards. As High As Fuel is 10 live cards. The main Fuel tee uses the white and heather photos only. Of the newer print-ready DTG files, only Fuel pack 3 is here: Premium Grade Only, Check Engine Chill Mode, and Slow Lane High Life (`shop/print-ready/fuel/`). The other 6 Fuel slogan prints and all 6 Gothic fill prints are not on this site. Do not invent them. Brush & Smoke is 4 preview cards. Biomechanical is the Half Machine Skull preview card.
- Wave-1 prices are locked if those products are added later: hoodie AU$75, AOP beanie AU$49, Flexfit AU$55. No mockups for them are on this site, so they are not in the catalog.
- Full Bleed is a live lane at 21 shop cards. Nebula Queen is held, so it is not one of those cards. Chest print is ready to list at 7. Living Screens is a live lane of wallpaper cards from the preview images on this site: Crimson Sun 9, Quiet Rain 8, plus Oni, Ronin Rain, Starbound, and Neon Cyberpunk collages and the two desktop shots. Pack price AU$12. Design still counts 57 packs; only the images in the preview zips are cards. The AU$10 add-on with a tee stays held, and the pack zip is not a separate download. Night Shift is seasonal, not an adults-only lane. Blackletter and As High As Fuel are live lanes. Their held marketing blurbs stay off the public shop. Demo checkout only. No deploy.
- Remove `<meta name="robots" content="noindex">` when Jason says the shop should be indexed. Test-mode Stripe still keeps the shop out of search.
- Stripe Checkout is ready and parked. Leave `STRIPE_SECRET_KEY` unset. Use `SHOP_PAYID` or `SHOP_CHECKOUT=demo` until Jason adds `sk_test_` later. Do not commit keys. The server rejects `sk_live_` / `rk_live_`. See README “Payments”.
- Free shipping on the Stripe session is Australia only. Do not add a zero shipping rate for other countries. Overseas postage stays closed until a charged rate is set.
- PayID (`SHOP_PAYID`) is the path when the Stripe secret is unset. It does not run alongside Stripe.

Demo checkout, used when Stripe and PayID are both unset, does not charge a card and does not send anything to print. A Stripe test payment is a real test-mode charge and still does not send the shirt to print by itself.
