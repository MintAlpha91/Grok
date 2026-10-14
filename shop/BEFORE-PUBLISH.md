# Before this shop goes live

This shop is a preview catalog, not a live store. Do not treat it as go-live ready until every collection has at least 10 items. A thin collection stays `upcoming` or `ready` (ready to list). It is not the public storefront. When Design supplies more art and mockups, add them to the catalog and move the lane toward that floor. Do not describe the site as open. A Railway preview is below; it stays `noindex` and does not turn Stripe on.

The website brand is Rogers Inc / Rogers Inc Designs. Elemental Wood is the Etsy shop name only.

Resolved by Jason (14 Oct 2026):

- Contact email for damaged or misprinted orders: rogersinc426@gmail.com (on the returns/shipping copy).
- Remake window: 7 days from delivery.
- Indexing: keep `noindex` for now.
- PayID: 0499420228, name Rogers Inc Designs. Set via deploy env (`SHOP_PAYID`, `SHOP_PAYID_NAME`); see `deploy.env.example`.

Also still open:

- This server stores the order. With SMTP set, it emails Jason on a new order, emails the customer PayID instructions, and emails tracking when Printful reports `package_shipped`. Without SMTP it logs and continues.
- Shirt photos are the Printful mockups in `public/mockups/{slug}-aop-poly.jpg` and `{slug}-aop-cotton.jpg`, cropped to 1280×720 so the caption strip is gone. The page price is the only price. Do not put the Printful caption (old AU$69 / AU$75) back on the photo. Pin crops for six designs are in the same folder and are not gallery tiles.
- Scene sentences live on each product in `catalog.json`. They were carried from the Etsy listing pack into Marketing’s blurb template. Marketing can replace `products.*.scene`.
- Jason cleared Gothic and As High As Fuel. Both lanes are live on the catalog, 10 cards each. As High As The Price Of Fuel shows white and heather only. Colour shots stay off the shop. The site is still demo checkout, not a deployed store.
- Crimson Sun Last Ronin is featured because the mockup is wired. Quiet Rain Umbrella Crossing and Window Seat are featured. Four Quiet Rain fills are in the catalog as upcoming, not on the shop: Ramen Steam Alley, Bus Stop Downpour, Vending Glow Puddle, Quiet Lantern Bridge. They are print-ready and the mockups are not on this site. Jason cleared Nebula Queen. It is live in Full Bleed / Starbound at polyester AU$65. Cotton stays the held AU$71 fabric until first sales. The shop photo is `nebula-queen-nudge-down-shirt-mockup.jpg` only. The print file is `print-ready/aop/Rogers-Inc-Designs-starbound-nebula-queen-aop-nudge-down-4500x5400.png`. Do not use the centered, fill, front-chest, or older poly/cotton mockups. The chest print of that scene stays held.
- Blackletter is 10 live cards. As High As Fuel is 10 live cards. The main Fuel tee uses the white and heather photos only. Print-ready DTG files are 4500×5400 RGB on white, stored under `shop/print-ready/` for Printful later. They are not shop photos. Fuel prints are for white and heather only. On hand: all six Gothic fills (Blood Covenant, Iron Psalm, Wraith March, Bone Chapel, Hex Altar, Pale Reign) and all nine Fuel slogan prints (Too High To Care, Gas Money Went To This, Budget Went Up In Smoke, Running On Fumes, Empty Tank Full Heart, High Mileage Low Motivation, Premium Grade Only, Check Engine Chill Mode, Slow Lane High Life). Print-ready DTG files for the original four Blackletter cards (Void King, Ash Iron, Night Warden, Grave Shift) and the main As High As The Price Of Fuel tee are now in `shop/print-ready/gothic/` and `shop/print-ready/fuel/` (Fuel uses the nobox white RGB front; dark variant also present). Brush & Smoke is 4 preview cards. Biomechanical is the Half Machine Skull preview card.
- Wave-1 prices are locked if those products are added later: hoodie AU$75, AOP beanie AU$49, Flexfit AU$55. No mockups for them are on this site, so they are not in the catalog.
- Full Bleed is a live lane at 22 shop cards. Nebula Queen is one of those cards, polyester AU$65. Chest print is live at 10 (7 prior hero chests + Nine-Tail Shrine, Chrome Crow Storm, Astral Fox Empress with black-bar-fixed mockups). Nebula Queen chest stays held. Print-ready files for the 3 new chests are under `shop/print-ready/chest/` as 4500×5400 RGB on white. They are not shop photos. Living Screens is a live lane of wallpaper cards from the preview images on this site: Crimson Sun 9, Quiet Rain 8, plus Oni, Ronin Rain, Starbound, and Neon Cyberpunk collages and the two desktop shots. Pack price AU$12. Design still counts 57 packs; only the images in the preview zips are cards. The AU$10 add-on with a tee stays held, and the pack zip is not a separate download. Night Shift is seasonal, not an adults-only lane. Blackletter and As High As Fuel are live lanes. Their held marketing blurbs stay off the public shop. Demo checkout only. Hosting this preview on Railway is below.
- Keep `noindex` (Jason, 14 Oct). Remove `<meta name="robots" content="noindex">` only when Jason says the shop should be indexed. Test-mode Stripe still keeps the shop out of search.
- Stripe Checkout is ready and parked. Leave `STRIPE_SECRET_KEY` unset. Use `SHOP_PAYID` or `SHOP_CHECKOUT=demo` until Jason adds `sk_test_` later. Do not commit keys. The server rejects `sk_live_` / `rk_live_`. See README “Payments”.
- Free shipping on the Stripe session is Australia only. Do not add a zero shipping rate for other countries. Overseas postage stays closed until a charged rate is set.
- PayID (`SHOP_PAYID`) is the path when the Stripe secret is unset. It does not run alongside Stripe.

Demo checkout, used when Stripe and PayID are both unset, does not charge a card and does not send anything to print. A Stripe test payment is a real test-mode charge and still does not send the shirt to print by itself.

## Railway

Host the preview from the `shop/` directory. In the Railway service, set Root Directory to `shop`. Config-as-code is not picked up from that root on its own, so set the config file path to `/shop/railway.json`. The start command is `PYTHONPATH=src python3 -m store`. `Procfile` and `nixpacks.toml` in `shop/` use the same command if the builder reads those instead.

Railway sets `PORT`. The process binds `0.0.0.0` on that port. The live service uses PayID checkout and stores orders at `SHOP_ORDERS_DIR=/data/orders`. Copy PayID from `deploy.env.example` (`SHOP_PAYID`, `SHOP_PAYID_NAME`). Leave `STRIPE_SECRET_KEY` unset. Keep `noindex`.

## Railway env vars

Set these on the Railway service. Do not commit the secret values.

Already on the service:

- `PORT` — Railway sets this. The shop binds `0.0.0.0` on it.
- `SHOP_PAYID` — `0499420228`.
- `SHOP_PAYID_NAME` — `Rogers Inc Designs`.
- `SHOP_ORDERS_DIR` — `/data/orders` (the volume mount).

Jason adds:

- `SHOP_ADMIN_PASSWORD` — a long password Jason chooses. It is not issued by a vendor. It unlocks `https://<railway-host>/admin`, which lists orders and has Mark paid. PayID cannot be confirmed by the bank, so this button is the payment switch.
- `PRINTFUL_API_KEY` — Printful private token. In Printful: Settings → API → Create token (private token). Copy it once; Printful does not show it again. Never commit it.
- `PRINTFUL_STORE_ID` — optional. Printful → Settings → Stores, the numeric store id. Set it when the token can see more than one store. Leave unset for a single-store token.
- `PRINTFUL_AUTO_CONFIRM` — leave unset or `false`. Mark paid then creates a Printful draft Jason can check before production. Set `true` only to submit the order for fulfilment immediately.
- `SHOP_ALERT_EMAIL` — inbox for each new order. If unset, the shop uses `rogersinc426@gmail.com`.
- `SMTP_HOST` — Gmail: `smtp.gmail.com`. Resend: `smtp.resend.com`.
- `SMTP_PORT` — `587`.
- `SMTP_USER` — the Gmail address, or `resend` for Resend SMTP.
- `SMTP_PASS` — Gmail app password, or a Resend API key used as the SMTP password. Gmail: Google Account → Security → turn on 2-Step Verification → App passwords → create one for Mail → paste the 16-character password. A normal Gmail password will not work.
- `SMTP_FROM` — the From address. For Gmail use `rogersinc426@gmail.com`. For Resend it must be an address on a domain verified in Resend.

Printful webhook: Settings → Webhooks → add `https://<railway-host>/api/printful/webhook` for the Package shipped event (`package_shipped`). That call stores the tracking number and emails the customer when SMTP is set.

Shirt map sent to Printful: polyester is product 257 (file type `default`), cotton is product 1414 (file type `front_dtfabric`), chest print is Bella+Canvas 3001 product 71 (file type `front`). Chest-print lane uses black. Gothic and As High As Fuel use white. Heather photos are not a separate Printful colour.

If `PRINTFUL_API_KEY` or the SMTP variables are missing, the shop logs the skip and still takes the order.
