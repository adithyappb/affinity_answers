#!/usr/bin/env python3
"""Extract product listings from MD Computers (mdcomputers.in) for a search term.

Usage:
    python mdcomputers_scraper.py "external harddrive"
    python mdcomputers_scraper.py "external harddrive" --format csv -o drives.csv
    python mdcomputers_scraper.py ssd --max-pages 1
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from typing import Iterator, Optional

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://mdcomputers.in/index.php"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)
REQUEST_TIMEOUT = 20      # seconds per request
PAGE_DELAY = 1.0          # polite pause between result pages

PAGE_COUNT_RE = re.compile(r"\((\d+)\s+Pages?\)", re.IGNORECASE)
PRODUCT_ID_RE = re.compile(r"cart\.add\('(\d+)'")
DIGITS_RE = re.compile(r"\d+")


@dataclass
class Product:
    product_id: Optional[str]
    name: str
    url: str
    price: Optional[int]          # selling price in INR
    mrp: Optional[int]            # struck-through list price in INR, if shown
    discount_percent: Optional[int]


# --------------------------------------------------------------------------- #
# Parsing (pure functions: HTML in, data out — easy to unit test offline)
# --------------------------------------------------------------------------- #
def parse_price(text: Optional[str]) -> Optional[int]:
    """'₹1,299' -> 1299. Returns None when no digits are present."""
    if not text:
        return None
    digits = "".join(DIGITS_RE.findall(text))
    return int(digits) if digits else None


def _text(node) -> Optional[str]:
    return node.get_text(" ", strip=True) if node else None


def parse_product(card) -> Optional[Product]:
    """Turn one `.product-grid-item` element into a Product."""
    link = card.select_one(".product-entities-title a")
    if link is None:
        return None

    price_box = card.select_one(".price")
    mrp = parse_price(_text(card.select_one(".price .del")))
    # Discounted items show the sale price in `.ins`; others show a bare amount.
    price = parse_price(_text(card.select_one(".price .ins")) or _text(price_box))
    discount = None
    if price and mrp and mrp > price:
        discount = round((mrp - price) * 100 / mrp)

    button = card.select_one("[onclick*='cart.add']")
    id_match = PRODUCT_ID_RE.search(button["onclick"]) if button else None

    return Product(
        product_id=id_match.group(1) if id_match else None,
        name=link.get_text(strip=True),
        url=link.get("href", ""),
        price=price,
        mrp=mrp,
        discount_percent=discount,
    )


def parse_page(html: str) -> tuple[list[Product], int]:
    """Return (products on this page, total number of result pages)."""
    soup = BeautifulSoup(html, "html.parser")
    # Scope to #content: headers/menus contain other product widgets.
    cards = soup.select("#content .product-grid-item")
    products = [p for p in map(parse_product, cards) if p is not None]

    match = PAGE_COUNT_RE.search(soup.get_text(" "))
    total_pages = int(match.group(1)) if match else (1 if products else 0)
    return products, total_pages


# --------------------------------------------------------------------------- #
# Fetching
# --------------------------------------------------------------------------- #
def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en-IN,en;q=0.9"})
    retry = Retry(total=3, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504))
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def fetch_page(session: requests.Session, term: str, page: int) -> str:
    params = {"route": "product/search", "search": term, "page": page}
    response = session.get(BASE_URL, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.text


def scrape(term: str, max_pages: Optional[int] = None) -> Iterator[Product]:
    """Yield products page by page until results (or max_pages) run out."""
    session = build_session()
    page, total_pages = 1, 1
    while page <= total_pages and (max_pages is None or page <= max_pages):
        products, total_pages = parse_page(fetch_page(session, term, page))
        if not products:
            break
        yield from products
        page += 1
        if page <= total_pages:
            time.sleep(PAGE_DELAY)


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
def write_json(products: list[Product], term: str, out) -> None:
    payload = {
        "query": term,
        "source": "https://mdcomputers.in",
        "scraped_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(products),
        "products": [asdict(p) for p in products],
    }
    json.dump(payload, out, indent=2, ensure_ascii=False)
    out.write("\n")


def write_csv(products: list[Product], out) -> None:
    writer = csv.DictWriter(out, fieldnames=[f.name for f in fields(Product)])
    writer.writeheader()
    writer.writerows(asdict(p) for p in products)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Scrape MD Computers search results.")
    parser.add_argument("term", nargs="+", help="search term, e.g. external harddrive")
    parser.add_argument("--format", choices=("json", "csv"), default="json")
    parser.add_argument("--max-pages", type=int, default=None,
                        help="stop after N result pages (default: all)")
    parser.add_argument("-o", "--output", help="write to file instead of stdout")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252

    term = " ".join(args.term).strip()
    try:
        products = list(scrape(term, args.max_pages))
    except requests.RequestException as exc:
        print(f"error: request failed: {exc}", file=sys.stderr)
        return 1

    out = open(args.output, "w", encoding="utf-8", newline="") if args.output else sys.stdout
    try:
        if args.format == "json":
            write_json(products, term, out)
        else:
            write_csv(products, out)
    finally:
        if out is not sys.stdout:
            out.close()

    print(f"{len(products)} products found for '{term}'", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
