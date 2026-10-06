"""Etsy field limits and Elemental Wood copy locks. No network."""

import re

TITLE_MAX = 140
TAG_COUNT = 13
TAG_MAX = 20

PRICE_LOCK = {
    "poly": {"price_aud": 69, "price_2xl_aud": 73, "printful_product": 257, "fabric_word": "polyester"},
    "cotton": {"price_aud": 75, "price_2xl_aud": 79, "printful_product": 1414, "fabric_word": "cotton"},
}

# Style words such as "anime" are allowed. These are claims or names the copy must not make.
BANNED_PATTERNS = (
    re.compile(r"\bbuilder\b", re.IGNORECASE),
    re.compile(r"officially\s+licensed", re.IGNORECASE),
    re.compile(r"\bofficial\s+(anime|merchandise|merch)\b", re.IGNORECASE),
    re.compile(r"\blicensed\s+(anime|merchandise|merch|character)\b", re.IGNORECASE),
    re.compile(
        r"\b(pokemon|pikachu|naruto|goku|dragon\s*ball|mario|nintendo|disney|marvel|"
        r"spider-?man|batman|hello\s+kitty|star\s+wars|one\s+piece|demon\s+slayer|"
        r"studio\s+ghibli|totoro|mickey)\b",
        re.IGNORECASE,
    ),
)

PRICE_IN_COPY = re.compile(r"AU\$(\d+)")


def validate_listing(listing: dict) -> list[str]:
    errors = []
    design = listing.get("design", "")
    fabric = listing.get("fabric", "")
    title = listing.get("title") or ""
    description = listing.get("description") or ""
    tags = listing.get("tags") or []
    label = f"{design} ({fabric or 'unknown fabric'})"

    if fabric not in PRICE_LOCK:
        errors.append(f"{label}: fabric must be poly or cotton")
        lock = None
    else:
        lock = PRICE_LOCK[fabric]

    if len(title) > TITLE_MAX:
        errors.append(f"{label}: title is {len(title)} characters; limit is {TITLE_MAX}")
    if not title.strip():
        errors.append(f"{label}: title is empty")
    credit = listing.get("studio_credit") or "Rogers Inc Designs"
    if credit not in title:
        errors.append(f"{label}: title must keep the {credit} credit")

    if not isinstance(tags, list):
        errors.append(f"{label}: tags must be a list")
        tags = []
    if len(tags) != TAG_COUNT:
        errors.append(f"{label}: expected {TAG_COUNT} tags, found {len(tags)}")
    seen = set()
    for tag in tags:
        text = tag if isinstance(tag, str) else ""
        if not isinstance(tag, str) or text.strip() != text or not text:
            errors.append(f"{label}: tag {tag!r} must be a non-empty string without surrounding space")
            continue
        if len(text) > TAG_MAX:
            errors.append(f"{label}: tag {text!r} is {len(text)} characters; limit is {TAG_MAX}")
        key = text.casefold()
        if key in seen:
            errors.append(f"{label}: duplicate tag {text!r}")
        seen.add(key)

    blob = f"{title}\n{description}\n" + "\n".join(t for t in tags if isinstance(t, str))
    for pattern in BANNED_PATTERNS:
        match = pattern.search(blob)
        if match:
            errors.append(f"{label}: banned wording {match.group(0)!r}")

    if "Original artwork" not in description:
        errors.append(f"{label}: description must say it is original artwork")

    if lock:
        if listing.get("price_aud") != lock["price_aud"]:
            errors.append(f"{label}: price_aud must be {lock['price_aud']}")
        if listing.get("price_2xl_aud") != lock["price_2xl_aud"]:
            errors.append(f"{label}: price_2xl_aud must be {lock['price_2xl_aud']}")
        if listing.get("printful_product") != lock["printful_product"]:
            errors.append(f"{label}: printful_product must be {lock['printful_product']}")
        if lock["fabric_word"] not in title.casefold() or lock["fabric_word"] not in description.casefold():
            errors.append(f"{label}: title and description must name the {lock['fabric_word']} fabric")
        other = "cotton" if fabric == "poly" else "polyester"
        if other in title.casefold():
            errors.append(f"{label}: title names the other fabric ({other})")
        amounts = {int(value) for value in PRICE_IN_COPY.findall(description)}
        expected = {lock["price_aud"], lock["price_2xl_aud"]}
        if amounts != expected:
            errors.append(
                f"{label}: description prices {sorted(amounts)} do not match locked {sorted(expected)}"
            )

    if listing.get("sizes") != "XS-2XL":
        errors.append(f"{label}: sizes must be XS-2XL")
    if listing.get("free_au_shipping") is not True:
        errors.append(f"{label}: free_au_shipping must be true")
    if "free shipping within Australia" not in description:
        errors.append(f"{label}: description must say free shipping within Australia")
    if not listing.get("slug"):
        errors.append(f"{label}: missing design slug")
    return errors
