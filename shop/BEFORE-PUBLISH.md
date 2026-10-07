# Before this shop goes live

The website brand is Rogers Inc / Rogers Inc Designs. Elemental Wood is the Etsy shop name only.

Jason still needs to confirm these. They are not invented on the site.

- Contact email for damaged or misprinted orders. None is set. The shipping page says the address is not published yet.
- Remake window. Marketing’s draft says email within 7 days of delivery. That number is not confirmed.

Also still open:

- This server stores the order. It does not send the “we’ll email when it ships” message itself.
- Drop real mockups in `public/art/{slug}.jpg` (or `.png` / `.webp`). Until then the product panels are colour fields, not the artwork.
- Scene sentences in `web-copy.json` were carried from the Etsy listing pack into Marketing’s blurb template. Marketing can replace `designs.*.scene`.
- Remove `<meta name="robots" content="noindex">` when payments are on and the shop should be indexed. Demo and off modes keep the shop out of search.

Demo checkout does not charge a card and does not send anything to print.
