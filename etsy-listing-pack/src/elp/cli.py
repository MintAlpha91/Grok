import argparse
from pathlib import Path

from elp.load import enrich, load_json
from elp.render import build_pack

ROOT = Path(__file__).resolve().parents[2]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Build paste-ready Etsy listing files. Does not log into Etsy or Printful."
    )
    parser.add_argument("--listings", default=str(ROOT / "data" / "marketing-aop-listings.json"))
    parser.add_argument("--slugs", default=str(ROOT / "data" / "design-slugs.json"))
    parser.add_argument("--progress", default=str(ROOT / "data" / "publish-status.json"))
    parser.add_argument("--out", default=str(ROOT / "out"))
    args = parser.parse_args(argv)
    progress = load_json(args.progress)
    listings = enrich(load_json(args.listings), load_json(args.slugs), progress)
    errors, report = build_pack(listings, args.out, progress.get("note", ""))
    print(f"Wrote {report}")
    if errors:
        print(f"{len(errors)} problem(s). No paste files were written.")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Wrote {len(listings)} paste-ready listings to {args.out}")
    return 0
