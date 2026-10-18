"""Indexing for the live Rogers Inc Designs shop.

Public pages on rogersincdesigns.com can be crawled. Admin, API, checkout,
order, and cart stay out of search on every host. Other hosts stay noindex.
"""

from __future__ import annotations

import os
import re
from xml.sax.saxutils import escape

from store.catalog import catalog_listed, load_catalog, public_collections

ORIGIN = "https://rogersincdesigns.com"
PRODUCTION_HOSTS = frozenset({"rogersincdesigns.com", "www.rogersincdesigns.com"})
PRIVATE_PREFIXES = ("/admin", "/api", "/checkout", "/order", "/cart")
TOKEN = re.compile(r"^[A-Za-z0-9_-]{8,200}$")
# Public site token. It is meant to appear in page source. CF_ANALYTICS_TOKEN overrides it.
PUBLIC_ANALYTICS_TOKEN = "781581d7a1804f0d828e30b4139f2f7a"

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self' https://static.cloudflareinsights.com; "
    "connect-src 'self' https://cloudflareinsights.com https://static.cloudflareinsights.com; "
    "img-src 'self' data:; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "base-uri 'self'; "
    "frame-ancestors 'none'"
)


def request_host(header: str) -> str:
    return (header or "").split(":")[0].strip().lower()


def canonical_path(path: str) -> str:
    path = (path or "/").split("?")[0]
    if not path.startswith("/"):
        path = "/" + path
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return path or "/"


def is_production_host(host: str) -> bool:
    return request_host(host) in PRODUCTION_HOSTS


def is_private_path(path: str) -> bool:
    path = canonical_path(path)
    return any(path == prefix or path.startswith(prefix + "/") for prefix in PRIVATE_PREFIXES)


def should_noindex(host: str, path: str) -> bool:
    return is_private_path(path) or not is_production_host(host)


def analytics_token(env: dict | None = None) -> str:
    env = os.environ if env is None else env
    token = (env.get("CF_ANALYTICS_TOKEN") or "").strip()
    if TOKEN.fullmatch(token):
        return token
    return PUBLIC_ANALYTICS_TOKEN


def beacon_tag(token: str) -> str:
    if not token:
        return ""
    return (
        '<script defer src="https://static.cloudflareinsights.com/beacon.min.js" '
        f'data-cf-beacon=\'{{"token": "{token}"}}\'></script>'
    )


def prepare_html(html: str, path: str, host: str, token: str = "") -> str:
    """Insert canonical, robots, and the analytics beacon into the storefront shell."""
    page = canonical_path(path)
    extras = [f'<link rel="canonical" href="{ORIGIN}{page if page != "/" else "/"}">']
    if should_noindex(host, page):
        extras.append('<meta name="robots" content="noindex">')
    if token and not is_private_path(page):
        extras.append(beacon_tag(token))
    block = "\n  ".join(extras)
    if 'rel="canonical"' in html:
        html = re.sub(r'\s*<link rel="canonical" href="[^"]*">', "", html, count=1)
    return html.replace("</head>", f"  {block}\n</head>", 1)


def robots_txt() -> str:
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin",
        "Disallow: /api",
        "Disallow: /checkout",
        "Disallow: /order",
        "Disallow: /cart",
        "",
        f"Sitemap: {ORIGIN}/sitemap.xml",
        "",
    ]
    return "\n".join(lines)


def sitemap_paths() -> list[str]:
    catalog = load_catalog()
    paths = ["/", "/shop", "/about", "/shipping"]
    for item in public_collections(catalog):
        landing = str(item.get("landing") or item["id"]).strip("/")
        if landing:
            paths.append(f"/collection/{landing}")
    for product in catalog["products"]:
        if catalog_listed(product):
            paths.append(f"/product/{product['slug']}")
    seen = []
    for path in paths:
        if path not in seen and not is_private_path(path):
            seen.append(path)
    return seen


def sitemap_xml() -> str:
    urls = []
    for path in sitemap_paths():
        loc = escape(f"{ORIGIN}{path}")
        urls.append(f"  <url><loc>{loc}</loc></url>")
    body = "\n".join(urls)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n"
        "</urlset>\n"
    )
