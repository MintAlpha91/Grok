import json
from pathlib import Path


def load_json(path: str | Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def enrich(listings: list, slugs: dict, progress: dict) -> list[dict]:
    by_design = {row["design"]: row["slug"] for row in slugs["designs"]}
    known = {
        (row["slug"], row["fabric"]): row
        for row in progress.get("known", [])
    }
    enriched = []
    for raw in listings:
        item = dict(raw)
        item["slug"] = by_design.get(raw.get("design", ""))
        match = known.get((item["slug"], item.get("fabric")))
        if match and match.get("state") == "live":
            item["publish_state"] = "live"
            item["etsy_url"] = match.get("etsy_url")
            item["etsy_listing_id"] = match.get("etsy_listing_id")
            item["printful_template_id"] = match.get("printful_template_id")
        elif match:
            item["publish_state"] = match.get("state") or "not_published"
            item["etsy_url"] = match.get("etsy_url")
            item["etsy_listing_id"] = match.get("etsy_listing_id")
            item["printful_template_id"] = match.get("printful_template_id")
        else:
            item["publish_state"] = "not_published"
            item["etsy_url"] = None
            item["etsy_listing_id"] = None
            item["printful_template_id"] = None
        enriched.append(item)
    return enriched
