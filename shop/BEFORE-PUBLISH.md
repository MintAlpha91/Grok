# Before this shop goes live

The website brand is Rogers Inc / Rogers Inc Designs. Elemental Wood is the Etsy shop name only.

Jason still needs to confirm these. They are not invented on the site.

- Contact email for damaged or misprinted orders. None is set. The shipping page says the address is not published yet.
- Remake window. Marketing’s draft says email within 7 days of delivery. That number is not confirmed.

Also still open:

- This server stores the order. It does not send the “we’ll email when it ships” message itself.
- Shirt photos are the Printful mockups in `public/mockups/{slug}-aop-poly.jpg` and `{slug}-aop-cotton.jpg`. Pin crops for six designs are in the same folder.
- Scene sentences live on each product in `catalog.json`. They were carried from the Etsy listing pack into Marketing’s blurb template. Marketing can replace `products.*.scene`.
- The first live collection is the AOP wave. Gothic blackletter, stoner, and calligraphy are upcoming collections in the same file. “As High As Fuel” is an example on the stoner lane, not a product.
- Remove `<meta name="robots" content="noindex">` when payments are on and the shop should be indexed. Demo and off modes keep the shop out of search.

Demo checkout does not charge a card and does not send anything to print.
