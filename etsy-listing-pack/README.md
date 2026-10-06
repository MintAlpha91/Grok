# Etsy listing pack

Paste-ready copy for 16 Elemental Wood all-over-print shirts: 8 original designs, polyester and cotton. The tool reads Marketing's JSON, checks Etsy field limits and the locked prices, and writes files Jason or Jarvis can paste.

It does not log into Etsy or Printful, and it does not publish.

## Locked facts

- Polyester AU$69, 2XL AU$73. Printful product 257.
- Cotton AU$75, 2XL AU$79. Printful product 1414.
- GST included. Free shipping within Australia. Sizes XS to 2XL only.
- Titles must be 140 characters or fewer. Each listing has 13 tags, and each tag is 20 characters or fewer.
- Copy stays original art credited to Rogers Inc Designs. It rejects "builder", official-license claims, and a short list of trademarked character and studio names.
- One listing is already live: Last Ronin polyester, https://www.etsy.com/listing/4589600597 (Printful template 108436673). The other 15 stay unpublished until Jason says go.

## Run

Python 3.12. No packages to install.

```bash
cd etsy-listing-pack
PYTHONPATH=src python3 -m elp
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

`python3 -m elp` reads `data/marketing-aop-listings.json`, joins `data/design-slugs.json`, and marks live rows from `data/publish-status.json`. Output lands in `out/`. Exit code 1 means a listing failed QA and no paste files were written.

## What to paste

Open `out/INDEX.md`, then the matching file in `out/listings/`.

- **Title**, **Description**, and the 13 **Tags** are the blocks to paste into the Etsy editor.
- `out/listings.csv` is the same text in one sheet, with `tag_1` through `tag_13`.
- `out/listings.json` is the same pack for another script.
- The Last Ronin polyester file is for comparison with the live listing. Do not create that listing again.
- Files marked `not_published` or `template_only` wait until Jason says go.

Design names in the Marketing JSON join to these slugs: `crimson-sun-last-ronin`, `oni-mask-crimson-oni`, `quiet-rain-umbrella-crossing`, `quiet-rain-window-seat`, `starbound-nebula-queen`, `neon-dual-blade-alley`, `ronin-ghost-armour`, `ronin-last-stand`.

## Portfolio demo

`demo-out/` is a two-design sample you can show a buyer. The artwork names are fictional (Paper Boat Harbour and Greenhouse Moon, credited to Lumen Sample Studio). It does not use the live shop name, live titles, or live tags. Prices are the same placeholders: polyester AU$69 (2XL AU$73) and cotton AU$75 (2XL AU$79). Nothing in the demo is for sale, and the command does not log into Etsy.

Show `demo-out/INDEX.md`, then open one file under `demo-out/listings/`. Regenerate it with:

```bash
cd etsy-listing-pack
PYTHONPATH=src python3 -m elp \
  --listings data/demo-listings.json \
  --slugs data/demo-slugs.json \
  --progress data/demo-publish-status.json \
  --out demo-out
```
