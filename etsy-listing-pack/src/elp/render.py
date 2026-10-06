import csv
import json
from pathlib import Path

from elp.rules import TAG_COUNT, validate_listing


def build_pack(
    listings: list[dict],
    out_dir: str | Path,
    progress_note: str,
    index_title: str | None = None,
    index_hint: str | None = None,
) -> tuple[list[str], Path]:
    out = Path(out_dir)
    listing_dir = out / "listings"
    listing_dir.mkdir(parents=True, exist_ok=True)
    errors = []
    for listing in listings:
        errors.extend(validate_listing(listing))
    if errors:
        report = out / "QA.md"
        report.write_text(_qa(listings, errors, progress_note), encoding="utf-8")
        return errors, report

    payload = [_public_row(listing) for listing in listings]
    (out / "listings.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_csv(out / "listings.csv", payload)
    for listing in listings:
        path = listing_dir / f"{listing['slug']}-{listing['fabric']}.md"
        path.write_text(_markdown(listing), encoding="utf-8")
    report = out / "QA.md"
    report.write_text(_qa(listings, [], progress_note), encoding="utf-8")
    (out / "INDEX.md").write_text(
        _index(listings, progress_note, index_title, index_hint),
        encoding="utf-8",
    )
    return [], report


def _public_row(listing: dict) -> dict:
    row = {
        "slug": listing["slug"],
        "design": listing["design"],
        "fabric": listing["fabric"],
        "publish_state": listing["publish_state"],
        "title": listing["title"],
        "title_chars": len(listing["title"]),
        "description": listing["description"],
        "price_aud": listing["price_aud"],
        "price_2xl_aud": listing["price_2xl_aud"],
        "sizes": listing["sizes"],
        "free_au_shipping": listing["free_au_shipping"],
        "printful_product": listing["printful_product"],
        "printful_template_id": listing.get("printful_template_id"),
        "etsy_listing_id": listing.get("etsy_listing_id"),
        "etsy_url": listing.get("etsy_url"),
        "tags": listing["tags"],
    }
    return row


def _write_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = [
        "slug",
        "design",
        "fabric",
        "publish_state",
        "title",
        "title_chars",
        "description",
        "price_aud",
        "price_2xl_aud",
        "sizes",
        "free_au_shipping",
        "printful_product",
        "printful_template_id",
        "etsy_listing_id",
        "etsy_url",
    ] + [f"tag_{index}" for index in range(1, TAG_COUNT + 1)]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for row in rows:
            flat = {key: row.get(key) for key in fieldnames if not key.startswith("tag_")}
            for index, tag in enumerate(row["tags"], start=1):
                flat[f"tag_{index}"] = tag
            writer.writerow(flat)


def _markdown(listing: dict) -> str:
    state = listing["publish_state"]
    if state == "live":
        banner = (
            f"Already live at {listing['etsy_url']}. "
            "Use this file to compare copy. Do not create a second listing."
        )
    else:
        banner = listing.get("paste_note") or (
            "Not published. Paste into Etsy only after Jason says go. "
            "This file does not log in and does not publish."
        )
    tags = "\n".join(f"{index}. {tag}" for index, tag in enumerate(listing["tags"], start=1))
    template = listing.get("printful_template_id")
    template_line = f"{template}\n" if template else "none recorded\n"
    return (
        f"# {listing['design']} ({listing['fabric']})\n\n"
        f"{banner}\n\n"
        f"- Slug: {listing['slug']}\n"
        f"- Publish state: {state}\n"
        f"- Price: AU${listing['price_aud']} (2XL AU${listing['price_2xl_aud']}), GST included\n"
        f"- Sizes: XS to 2XL only\n"
        f"- Shipping: free within Australia\n"
        f"- Printful product id: {listing['printful_product']}\n"
        f"- Printful template id: {template_line}\n"
        f"## Title ({len(listing['title'])} characters)\n\n"
        f"{listing['title']}\n\n"
        f"## Description\n\n"
        f"{listing['description']}\n\n"
        f"## Tags (13)\n\n"
        f"{tags}\n"
    )


def _index(listings: list[dict], note: str, title: str | None, hint: str | None) -> str:
    lines = [
        f"# {title or 'Elemental Wood AOP listing pack'}",
        "",
        note,
        "",
        hint
        or "Paste from `listings/*.md` or from `listings.csv`. The live row is for comparison. `not_published` and `template_only` rows wait until Jason says go.",
        "",
        "| Slug | Fabric | State | Price | Title characters |",
        "|---|---|---|---|---|",
    ]
    for listing in listings:
        lines.append(
            f"| {listing['slug']} | {listing['fabric']} | {listing['publish_state']} | "
            f"AU${listing['price_aud']} (2XL AU${listing['price_2xl_aud']}) | {len(listing['title'])} |"
        )
    lines.append("")
    return "\n".join(lines)


def _qa(listings: list[dict], errors: list[str], note: str) -> str:
    lines = [
        "# Listing pack QA",
        "",
        note,
        "",
        f"- Listings: {len(listings)}",
        f"- Problems: {len(errors)}",
        "",
    ]
    if errors:
        lines.append("## Problems")
        lines.append("")
        lines.extend(f"- {error}" for error in errors)
    else:
        lines.append("Title length, tag count, tag length, locked prices, and banned wording all passed.")
    lines.append("")
    return "\n".join(lines)
