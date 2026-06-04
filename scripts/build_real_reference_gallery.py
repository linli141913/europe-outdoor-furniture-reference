#!/usr/bin/env python3
"""Build a local real-product reference gallery for HDPE / poly lumber chairs.

The output intentionally favors verifiable brand / ecommerce product pages over
Pinterest-style reposts, and filters out monobloc, rattan/wicker, Adirondack,
folding/camping, fabric sling, and chaise/sun-lounger references.
"""

from __future__ import annotations

import csv
import html
import json
import re
import sys
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "reference_gallery"
JSON_OUT = OUT_DIR / "images.json"
CSV_OUT = OUT_DIR / "gallery.csv"
HTML_OUT = OUT_DIR / "index.html"
FAVORITES_HTML_OUT = OUT_DIR / "favorites.html"
FAVORITES_JSON = OUT_DIR / "favorites.json"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

SHOPIFY_SOURCES = [
    {
        "name": "POLYWOOD",
        "base": "https://www.polywood.com",
        "trust": "HDPE / poly lumber brand",
        "max_pages": 10,
        "page_limit": 50,
        "max_products": 140,
        "max_images": 12,
        "default_category": "A | HDPE / poly lumber 主参考",
    },
    {
        "name": "Trex Outdoor Furniture",
        "base": "https://www.trexfurniture.com",
        "trust": "HDPE / poly lumber brand",
        "max_pages": 8,
        "page_limit": 50,
        "max_products": 100,
        "max_images": 12,
        "default_category": "A | HDPE / poly lumber 主参考",
    },
    {
        "name": "highwood",
        "base": "https://highwood-usa.com",
        "trust": "HDPE / synthetic wood brand",
        "max_pages": 8,
        "page_limit": 50,
        "max_products": 90,
        "max_images": 12,
        "default_category": "A | HDPE / poly lumber 主参考",
    },
    {
        "name": "Winawood",
        "base": "https://winawood.co.uk",
        "trust": "recycled polymer garden furniture",
        "max_pages": 3,
        "page_limit": 50,
        "max_products": 70,
        "max_images": 12,
        "default_category": "B | 欧洲花园直板条参考",
    },
    {
        "name": "Sun Country Leisure",
        "base": "https://suncountryleisure.com",
        "trust": "retailer: C.R. Plastics / recycled plastic products",
        "max_pages": 4,
        "page_limit": 50,
        "max_products": 90,
        "max_images": 12,
        "default_category": "D | 零售平台补充",
    },
    {
        "name": "Terra Outdoor",
        "base": "https://terraoutdoor.com",
        "trust": "modern outdoor retailer, plastic lamella references",
        "max_pages": 4,
        "page_limit": 50,
        "max_products": 60,
        "max_images": 12,
        "default_category": "C | 现代塑料板条造型参考",
    },
    {
        "name": "Loll Designs",
        "base": "https://lolldesigns.com",
        "trust": "flat-panel recycled plastic furniture brand",
        "max_pages": 1,
        "page_limit": 50,
        "max_products": 25,
        "max_images": 12,
        "default_category": "C | 平板化装配思路参考",
    },
]

SITEMAP_SOURCES = []

SEED_PAGES = [
    {
        "source": "TDP",
        "url": "https://www.tdp.co.uk/product/derwent-chair/",
        "category": "B | 欧洲花园直板条参考",
        "trust": "UK recycled plastic furniture",
    },
    {
        "source": "Winawood",
        "url": "https://winawood.co.uk/products/sandwick-armchair",
        "category": "B | 欧洲花园直板条参考",
        "trust": "recycled polymer garden furniture",
    },
    {
        "source": "POLYWOOD",
        "url": "https://www.polywood.com/products/vineyard-garden-arm-chair-gnb24",
        "category": "A | HDPE / poly lumber 主参考",
        "trust": "HDPE / poly lumber brand",
    },
    {
        "source": "Trex Outdoor Furniture",
        "url": "https://www.trexfurniture.com/products/yacht-club-garden-arm-chair-txb24",
        "category": "A | HDPE / poly lumber 主参考",
        "trust": "HDPE / poly lumber brand",
    },
    {
        "source": "highwood",
        "url": "https://highwood-usa.com/products/lehigh-garden-chair",
        "category": "A | HDPE / poly lumber 主参考",
        "trust": "HDPE / synthetic wood brand",
    },
    {
        "source": "Sun Country Leisure",
        "url": "https://suncountryleisure.com/products/cr-plastics-c323-napa-dining-arm-chair",
        "category": "D | 零售平台补充",
        "trust": "retailer: C.R. Plastics / recycled plastic products",
    },
    {
        "source": "Patio Contract",
        "url": "https://www.patiocontract.com/product/ssc602",
        "category": "D | 零售平台补充",
        "trust": "retailer: Seaside Casual recycled plastic chair",
    },
    {
        "source": "Terra Outdoor",
        "url": "https://terraoutdoor.com/products/reclips-dining-arm-chair-black-bamboo",
        "category": "C | 现代塑料板条造型参考",
        "trust": "modern plastic lamella reference",
    },
    {
        "source": "LuxeDecor",
        "url": "https://www.luxedecor.com/product/seaside-casual-greenwich-recycled-plastic-patio-dining-chair-ssc602",
        "category": "D | 零售平台补充",
        "trust": "retailer: Seaside Casual recycled plastic chair",
    },
    {
        "source": "Patio Productions",
        "url": "https://www.patioproductions.com/murphy-poly-dining-arm-chair-mdp-by-berlin-gardens.html",
        "category": "D | 零售平台补充",
        "trust": "retailer: Berlin Gardens poly lumber chair",
    },
]


TITLE_INCLUDE = re.compile(
    r"\b("
    r"garden\s+arm|garden\s+chair|dining\s+arm|arm\s*chair|armchair|"
    r"patio\s+chair|outdoor\s+chair|side\s+chair|deck\s+chair|"
    r"cafe\s+chair|café\s+chair|chair"
    r")\b",
    re.I,
)

MATERIAL_INCLUDE = re.compile(
    r"\b("
    r"hdpe|polywood|poly\s+lumber|poly-lumber|poly\s+chair|recycled\s+plastic|"
    r"plastic\s+lumber|recycled\s+poly|recycled\s+polymer|envirowood|"
    r"winawood|trex|highwood|c\.?r\.?\s+plastic|cr\s+plastics|"
    r"seaside\s+casual|tdp|loll|reclips|lamella|slatted|slat"
    r")\b",
    re.I,
)

PRODUCT_EXCLUDE = re.compile(
    r"\b("
    r"adirondack|rattan|wicker|woven|weave|rope|cane|monobloc|monoblock|"
    r"chaise|sun\s*lounger|lounger|sunbed|daybed|folding|foldable|camping|"
    r"metal\s+folding|sling|fabric|canvas|mesh|hammock|rocking|rocker|glider|"
    r"swivel|stacking|stackable|bar|counter|stool|bench|"
    r"ottoman|sofa|loveseat|sectional|deep\s+seating|cushion|pad|cover|table|"
    r"quick-dry|quick\s+dry|armless|modular|corner|"
    r"side\s+chair|without\s+armrests?|without\s+arms?|"
    r"in-pool|pool\s+chair|kids?|children|"
    r"set|5-piece|4-piece|3-piece|2-piece|bundle|replacement|hardware"
    r")\b",
    re.I,
)

IMAGE_EXCLUDE = re.compile(
    r"("
    r"logo|favicon|icon|sprite|payment|visa|mastercard|paypal|badge|seal|"
    r"swatch|sample|color-chip|colour-chip|fabric|cushion|diagram|dimension|"
    r"dimensions|spec|assembly|manual|pdf|placeholder|avatar|newsletter|"
    r"instagram|facebook|youtube|pinterest|trustpilot|warranty|lifestyle|scene|detail|closeup|close-up|"
    r"sofa|ottoman|bench|picnic|swing|kids?|children|child"
    r")",
    re.I,
)

IMAGE_URL_RE = re.compile(
    r"https?:\\?/\\?/[^\"'()<>\s]+?\.(?:jpe?g|png|webp)(?:\?[^\"'()<>\s]*)?",
    re.I,
)


@dataclass
class Product:
    source: str
    title: str
    url: str
    category: str
    trust: str
    description: str
    tags: list[str]
    images: list[str]


class ImageHTMLParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.images: list[str] = []
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k.lower(): (v or "") for k, v in attrs}
        if tag in {"img", "source"}:
            for key in (
                "src",
                "data-src",
                "data-original",
                "data-zoom",
                "data-large",
                "data-image",
                "data-image-src",
            ):
                if attr.get(key):
                    self.images.append(normalize_url(attr[key], self.base_url))
            for key in ("srcset", "data-srcset"):
                if attr.get(key):
                    best = best_srcset_url(attr[key], self.base_url)
                    if best:
                        self.images.append(best)
        elif tag == "meta":
            name = attr.get("property") or attr.get("name") or ""
            content = attr.get("content") or ""
            if content and name.lower() in {
                "og:image",
                "og:image:secure_url",
                "twitter:image",
                "twitter:image:src",
            }:
                self.images.append(normalize_url(content, self.base_url))
            if content and name.lower() in {"og:title", "twitter:title"}:
                self.meta[name.lower()] = content
        elif tag == "link":
            rel = attr.get("rel", "")
            href = attr.get("href", "")
            if href and "image_src" in rel:
                self.images.append(normalize_url(href, self.base_url))


def log(message: str) -> None:
    print(message, flush=True)


def fetch_text(url: str, timeout: int = 18, retries: int = 1) -> str:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
                },
            )
            with urlopen(req, timeout=timeout) as response:
                raw = response.read()
                charset = response.headers.get_content_charset() or "utf-8"
                return raw.decode(charset, "ignore")
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            last_error = exc
            time.sleep(0.6 * (attempt + 1))
    raise RuntimeError(f"fetch failed: {url}: {last_error}")


def normalize_url(value: str, base_url: str) -> str:
    value = html.unescape(value).strip().strip("\"'")
    value = value.replace("\\/", "/")
    if value.startswith("//"):
        value = "https:" + value
    return urljoin(base_url, value)


def best_srcset_url(srcset: str, base_url: str) -> str:
    candidates: list[tuple[int, str]] = []
    for part in srcset.split(","):
        pieces = part.strip().split()
        if not pieces:
            continue
        url = normalize_url(pieces[0], base_url)
        width = 0
        if len(pieces) > 1:
            m = re.search(r"(\d+)w", pieces[1])
            if m:
                width = int(m.group(1))
        candidates.append((width, url))
    if not candidates:
        return ""
    candidates.sort(reverse=True)
    return candidates[0][1]


def canonical_image_key(url: str) -> str:
    parsed = urlparse(url)
    query = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k.lower()
        not in {
            "width",
            "height",
            "format",
            "quality",
            "fit",
            "crop",
            "background",
            "bg",
            "auto",
            "dpr",
        }
    ]
    path = re.sub(r"(_|\-)(\d{2,4})x(\d{2,4})(?=\.)", "", parsed.path)
    path = re.sub(r"(_|\-)(\d{2,4})x(?=\.)", "", path)
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            "",
            urlencode(query),
            "",
        )
    )


def optimized_remote_preview(url: str) -> str:
    parsed = urlparse(url)
    if "cdn.shopify.com" not in parsed.netloc.lower():
        return url
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.setdefault("width", "640")
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            "",
            urlencode(query),
            "",
        )
    )


def clean_image_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    if not re.search(r"\.(jpe?g|png|webp)(\?|$)", parsed.path, re.I):
        return ""
    if IMAGE_EXCLUDE.search(url):
        return ""
    return url


def unique_images(urls: Iterable[str], max_images: int) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for url in urls:
        cleaned = clean_image_url(url)
        if not cleaned:
            continue
        key = canonical_image_key(cleaned)
        if key in seen:
            continue
        seen.add(key)
        output.append(cleaned)
        if len(output) >= max_images:
            break
    return output


def title_from_html(raw_html: str, parser: ImageHTMLParser) -> str:
    for key in ("og:title", "twitter:title"):
        if parser.meta.get(key):
            return html.unescape(parser.meta[key]).strip()
    m = re.search(r"<title[^>]*>(.*?)</title>", raw_html, re.I | re.S)
    if m:
        title = re.sub(r"\s+", " ", m.group(1))
        return html.unescape(title).strip()
    return ""


def reason_tags(text: str, source: str) -> list[str]:
    lower = text.lower()
    tags: list[str] = []
    if any(t in lower for t in ("hdpe", "poly lumber", "poly-lumber", "polywood", "highwood", "trex")):
        tags.append("HDPE / poly lumber")
    if any(t in lower for t in ("recycled plastic", "recycled polymer", "recycled poly", "envirowood")):
        tags.append("recycled plastic")
    if any(t in lower for t in ("slat", "slatted", "vineyard", "yacht club", "greenwich", "sandwick", "derwent")):
        tags.append("slatted")
    if any(t in lower for t in ("armchair", "arm chair", "dining arm", "garden arm")):
        tags.append("armchair")
    if any(t in lower for t in ("flat", "loll", "panel", "board", "reclips", "lamella")):
        tags.append("panel / flat-pack idea")
    if source in {"POLYWOOD", "Trex Outdoor Furniture", "highwood", "Loll Designs"}:
        tags.append("brand source")
    if not tags:
        tags.append("manual review")
    return tags


def clean_description(value: str, limit: int = 180) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    blocked = (
        "add to cart",
        "shipping",
        "newsletter",
        "privacy policy",
        "returns",
        "warranty",
    )
    lowered = text.lower()
    if any(term in lowered[:120] for term in blocked):
        return ""
    if len(text) > limit:
        return text[: limit - 1].rstrip() + "..."
    return text


def fallback_description(title: str, text: str) -> str:
    lower = f"{title} {text}".lower()
    pieces: list[str] = []
    if any(t in lower for t in ("hdpe", "polywood", "poly lumber", "poly-lumber", "trex", "highwood")):
        pieces.append("HDPE / poly lumber 户外椅")
    if any(t in lower for t in ("recycled plastic", "recycled polymer", "recycled poly", "tdp", "winawood")):
        pieces.append("再生塑料 / 聚合物材料")
    if any(t in lower for t in ("slat", "slatted", "garden", "vineyard", "yacht club", "lehigh", "derwent", "sandwick")):
        pieces.append("板条或可转化板件结构")
    if any(t in lower for t in ("armchair", "arm chair", "dining arm", "garden arm")):
        pieces.append("扶手椅比例")
    if not pieces:
        pieces.append("真实户外椅产品图，可点产品页复核结构")
    return "；".join(pieces) + "。"


def category_for(text: str, fallback: str) -> str:
    lower = text.lower()
    if any(t in lower for t in ("derwent", "sandwick", "winawood", "tdp", "straight", "slatted back")):
        return "B | 欧洲花园直板条参考"
    if any(t in lower for t in ("reclips", "lamella", "loll", "alfresco", "modern")):
        return "C | 现代塑料板条造型参考"
    if any(t in lower for t in ("seaside casual", "berlin gardens", "c.r. plastic", "cr plastics", "greenwich", "napa")):
        return "D | 零售平台补充"
    if any(t in lower for t in ("garden arm", "dining arm", "polywood", "trex", "highwood", "poly lumber", "hdpe")):
        return "A | HDPE / poly lumber 主参考"
    return fallback


def is_relevant_product(title: str, handle: str, body: str, source_name: str) -> bool:
    title_handle = f"{title} {handle}".lower()
    text = f"{title} {handle} {body}".lower()
    if PRODUCT_EXCLUDE.search(title_handle):
        return False
    if not TITLE_INCLUDE.search(title_handle):
        return False
    trusted_material_source = source_name in {
        "POLYWOOD",
        "Trex Outdoor Furniture",
        "highwood",
        "Winawood",
        "TDP",
        "Loll Designs",
    }
    if trusted_material_source:
        return True
    return bool(MATERIAL_INCLUDE.search(text))


def product_url_from_base(base: str, handle: str) -> str:
    return f"{base.rstrip('/')}/products/{handle}"


def collect_shopify_products(source: dict) -> list[Product]:
    base = source["base"].rstrip("/")
    products: list[Product] = []
    seen_handles: set[str] = set()
    for page in range(1, source.get("max_pages", 4) + 1):
        page_limit = source.get("page_limit", 50)
        url = f"{base}/products.json?limit={page_limit}&page={page}"
        try:
            data = json.loads(fetch_text(url))
        except Exception as exc:
            log(f"  ! {source['name']} products.json page {page}: {exc}")
            break
        batch = data.get("products") or []
        log(f"    page {page}: {len(batch)} products")
        if not batch:
            break
        for item in batch:
            title = str(item.get("title") or "").strip()
            handle = str(item.get("handle") or "").strip()
            if not title or not handle or handle in seen_handles:
                continue
            seen_handles.add(handle)
            body = re.sub(r"<[^>]+>", " ", str(item.get("body_html") or ""))
            tags = " ".join(map(str, item.get("tags") or []))
            vendor = str(item.get("vendor") or "")
            if not is_relevant_product(title, handle, f"{body} {tags} {vendor}", source["name"]):
                continue
            image_urls = []
            for image in item.get("images") or []:
                src = image.get("src")
                if src:
                    image_urls.append(normalize_url(src, base))
            image_urls = unique_images(image_urls, source.get("max_images", 8))
            if not image_urls:
                continue
            text = f"{title} {handle} {body} {tags} {vendor} {source['name']}"
            products.append(
                Product(
                    source=source["name"],
                    title=title,
                    url=product_url_from_base(base, handle),
                    category=category_for(text, source["default_category"]),
                    trust=source["trust"],
                    description=clean_description(str(item.get("body_html") or "")) or fallback_description(title, text),
                    tags=reason_tags(text, source["name"]),
                    images=image_urls,
                )
            )
            if len(products) >= source.get("max_products", 80):
                return products
    return products


def sitemap_urls(url: str) -> list[str]:
    try:
        raw = fetch_text(url)
    except Exception as exc:
        log(f"  ! sitemap failed {url}: {exc}")
        return []
    try:
        root = ElementTree.fromstring(raw.encode("utf-8"))
    except ElementTree.ParseError:
        return []
    urls: list[str] = []
    for elem in root.iter():
        if elem.tag.endswith("loc") and elem.text:
            urls.append(elem.text.strip())
    return urls


def extract_page_product(source: str, url: str, category: str, trust: str, max_images: int) -> Product | None:
    try:
        raw = fetch_text(url, timeout=12, retries=1)
    except Exception as exc:
        log(f"  ! page failed {url}: {exc}")
        return None
    parser = ImageHTMLParser(url)
    try:
        parser.feed(raw)
    except Exception:
        pass
    images = list(parser.images)
    for match in IMAGE_URL_RE.finditer(raw):
        images.append(normalize_url(match.group(0), url))
    images = unique_images(images, max_images)
    title = title_from_html(raw, parser) or urlparse(url).path.strip("/").split("/")[-1].replace("-", " ").title()
    visible_text = re.sub(r"<[^>]+>", " ", raw[:120000])
    text = f"{title} {url} {visible_text} {source}"
    if not images:
        return None
    if not is_relevant_product(title, url, visible_text, source):
        if source not in {"Patio Contract", "LuxeDecor", "Poly Lumber Furniture", "Patio Productions", "Fifthroom"}:
            return None
    return Product(
        source=source,
        title=title,
        url=url,
        category=category_for(text, category),
        trust=trust,
        description=fallback_description(title, text),
        tags=reason_tags(text, source),
        images=images,
    )


def extract_shopify_seed_product(source: str, url: str, category: str, trust: str, max_images: int) -> Product | None:
    parsed = urlparse(url)
    match = re.search(r"/products/([^/?#]+)", parsed.path)
    if not match:
        return None
    base = f"{parsed.scheme}://{parsed.netloc}"
    handle = match.group(1)
    product_json_url = f"{base}/products/{handle}.js"
    try:
        data = json.loads(fetch_text(product_json_url, timeout=12, retries=1))
    except Exception:
        return None
    title = str(data.get("title") or handle.replace("-", " ").title()).strip()
    body = re.sub(r"<[^>]+>", " ", str(data.get("description") or data.get("body_html") or ""))
    image_urls: list[str] = []
    for image in data.get("images") or []:
        if isinstance(image, str):
            image_urls.append(normalize_url(image, base))
        elif isinstance(image, dict) and image.get("src"):
            image_urls.append(normalize_url(str(image["src"]), base))
    images = unique_images(image_urls, max_images)
    if not images:
        return None
    text = f"{title} {handle} {body} {source}"
    return Product(
        source=source,
        title=title,
        url=url,
        category=category_for(text, category),
        trust=trust,
        description=clean_description(str(data.get("description") or data.get("body_html") or "")) or fallback_description(title, text),
        tags=reason_tags(text, source),
        images=images,
    )


def collect_sitemap_products(source: dict) -> list[Product]:
    products: list[Product] = []
    seen_urls: set[str] = set()
    for sitemap in source["urls"]:
        for url in sitemap_urls(sitemap):
            if url in seen_urls:
                continue
            seen_urls.add(url)
            slug = urlparse(url).path.lower()
            if not any(t in slug for t in ("chair", "seat", "armchair")):
                continue
            if PRODUCT_EXCLUDE.search(slug):
                continue
            product = extract_page_product(
                source["name"],
                url,
                source["default_category"],
                source["trust"],
                source.get("max_images", 8),
            )
            if product:
                products.append(product)
            if len(products) >= source.get("max_products", 60):
                return products
    return products


def flatten_products(products: list[Product]) -> list[dict]:
    entries: list[dict] = []
    seen_images: set[str] = set()
    for product in products:
        product_key = re.sub(r"[^a-z0-9]+", "-", f"{product.source}-{product.title}".lower()).strip("-")
        for index, image_url in enumerate(product.images[:1], 1):
            image_key = canonical_image_key(image_url)
            if image_key in seen_images:
                continue
            seen_images.add(image_key)
            entries.append(
                {
                    "id": f"{product_key}-{index:02d}",
                    "title": product.title,
                    "source": product.source,
                    "product_url": product.url,
                    "image_url": image_url,
                    "thumb_url": f"thumbs/{product_key}-{index:02d}.jpg"
                    if (OUT_DIR / "thumbs" / f"{product_key}-{index:02d}.jpg").exists()
                    else "",
                    "category": product.category,
                    "trust": product.trust,
                    "description": product.description,
                    "collapsed_count": len(product.images),
                    "tags": product.tags,
                }
            )
    return entries


def write_json(entries: list[dict]) -> None:
    JSON_OUT.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(entries: list[dict]) -> None:
    with CSV_OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "id",
                "title",
                "source",
                "category",
                "tags",
                "trust",
                "description",
                "collapsed_count",
                "model_key",
                "thumb_url",
                "product_url",
                "image_url",
            ],
        )
        writer.writeheader()
        for entry in entries:
            row = dict(entry)
            row["tags"] = "; ".join(entry["tags"])
            writer.writerow(row)


def stats(entries: list[dict]) -> dict:
    by_category: dict[str, int] = {}
    by_source: dict[str, int] = {}
    products: set[str] = set()
    for entry in entries:
        by_category[entry["category"]] = by_category.get(entry["category"], 0) + 1
        by_source[entry["source"]] = by_source.get(entry["source"], 0) + 1
        products.add(entry["product_url"])
    return {
        "images": len(entries),
        "products": len(products),
        "categories": by_category,
        "sources": by_source,
    }


def category_sort_key(category: str) -> int:
    order = [
        "板条 / 可转化结构",
        "塑料 / PP / 树脂",
        "金属 / 轻量庭院",
        "欧洲风格补充",
    ]
    return order.index(category) if category in order else len(order)


def read_favorites() -> set[str]:
    if not FAVORITES_JSON.exists():
        return set()
    try:
        data = json.loads(FAVORITES_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    if isinstance(data, list):
        return {str(item) for item in data}
    if isinstance(data, dict):
        return {str(item) for item in data.get("ids", [])}
    return set()


def write_favorites(ids: set[str]) -> None:
    FAVORITES_JSON.write_text(
        json.dumps(sorted(ids), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_html(entries: list[dict]) -> None:
    entry_ids = {entry["id"] for entry in entries}
    favorites = read_favorites() & entry_ids
    if favorites != read_favorites():
        write_favorites(favorites)

    favorite_entries = [entry for entry in entries if entry["id"] in favorites]

    def render_page(page_entries: list[dict], page_kind: str) -> str:
        visible_entries = favorite_entries if page_kind == "favorites" else page_entries
        s = stats(visible_entries)
        filter_stats = stats(page_entries)
        categories = sorted(filter_stats["categories"], key=category_sort_key)
        category_buttons = "\n".join(
            f'<button class="chip" data-filter="{html.escape(category)}">{html.escape(category)} '
            f'<span>{filter_stats["categories"][category]}</span></button>'
            for category in categories
        )
        cards = "\n".join(card_html(entry, favorites) for entry in page_entries)
        page_title = (
            "我的收藏夹"
            if page_kind == "favorites"
            else "HDPE / PE 板件户外扶手椅真实参考图库"
        )
        count_label = "款收藏" if page_kind == "favorites" else "款代表图"
        empty_text = (
            "收藏夹里还没有产品。回到全部产品页，点图片左上角星标即可收藏。"
            if page_kind == "favorites" and not page_entries
            else "当前筛选下没有图片。"
        )
        all_active = " active" if page_kind == "index" else ""
        favorites_active = " active" if page_kind == "favorites" else ""
        nav = f"""
        <nav class="page-nav" aria-label="页面切换">
          <a class="nav-link{all_active}" href="index.html">全部产品</a>
          <a class="nav-link{favorites_active}" href="favorites.html">收藏夹 <span id="favorite-count" data-count="{len(favorites)}">{len(favorites)}</span></a>
        </nav>
        """
        html_doc = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{page_title}</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #17201b;
      --muted: #66706a;
      --line: #d9dfd9;
      --soft: #f5f7f4;
      --accent: #2f6b57;
      --accent-2: #8f5f36;
      --card: #ffffff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: #fbfcfa;
    }}
    header {{
      position: sticky;
      top: 0;
      z-index: 3;
      background: rgba(251, 252, 250, 0.94);
      backdrop-filter: blur(14px);
      border-bottom: 1px solid var(--line);
    }}
    .wrap {{
      max-width: 1480px;
      margin: 0 auto;
      padding: 18px 24px;
    }}
    .title-row {{
      display: flex;
      gap: 18px;
      justify-content: space-between;
      align-items: flex-start;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: clamp(24px, 3vw, 38px);
      line-height: 1.1;
      letter-spacing: 0;
    }}
    .subtitle {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px 18px;
      color: var(--muted);
      font-size: 14px;
    }}
    .stats strong {{ color: var(--ink); }}
    .page-nav {{
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 8px;
      padding-top: 3px;
    }}
    .nav-link {{
      min-height: 34px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 0 13px;
      color: var(--ink);
      background: #fff;
      text-decoration: none;
      font-size: 13px;
      white-space: nowrap;
    }}
    .nav-link.active {{
      border-color: var(--accent);
      background: #e7f1ec;
      color: #14392d;
      font-weight: 700;
    }}
    .toolbar {{
      display: grid;
      grid-template-columns: minmax(220px, 1fr) auto;
      gap: 12px;
      align-items: center;
      margin-top: 16px;
    }}
    input[type="search"] {{
      width: 100%;
      min-height: 44px;
      border: 1px solid var(--line);
      border-radius: 7px;
      padding: 0 14px;
      background: white;
      color: var(--ink);
      font-size: 15px;
    }}
    .reset {{
      min-height: 44px;
      border: 1px solid var(--line);
      border-radius: 7px;
      padding: 0 14px;
      background: white;
      color: var(--ink);
      cursor: pointer;
    }}
    .filters {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 12px;
    }}
    .chip {{
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 8px 11px;
      background: white;
      color: var(--ink);
      cursor: pointer;
      font-size: 13px;
    }}
    .chip span {{
      color: var(--muted);
      margin-left: 4px;
    }}
    .chip.active {{
      border-color: var(--accent);
      background: #e7f1ec;
      color: #14392d;
    }}
    .note {{
      margin-top: 14px;
      padding: 12px 14px;
      background: #f1f4ef;
      border: 1px solid var(--line);
      border-radius: 7px;
      color: #3f4b44;
      font-size: 13px;
      line-height: 1.55;
    }}
    main.wrap {{ padding-top: 24px; }}
    .gallery {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 16px;
    }}
    article {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--card);
      overflow: hidden;
      display: flex;
      min-height: 100%;
      flex-direction: column;
    }}
    .thumb {{
      position: relative;
      display: block;
      aspect-ratio: 1 / 1;
      background: var(--soft);
      border-bottom: 1px solid var(--line);
      overflow: hidden;
    }}
    .thumb img {{
      width: 100%;
      height: 100%;
      object-fit: contain;
      display: block;
      mix-blend-mode: multiply;
    }}
    .delete-card {{
      position: absolute;
      top: 10px;
      right: 10px;
      width: 34px;
      height: 34px;
      border: 0;
      border-radius: 999px;
      background: #ff4751;
      color: #fff;
      font-size: 22px;
      line-height: 1;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 8px 22px rgba(255, 71, 81, 0.28);
      opacity: 0;
      transform: translateY(-4px);
      white-space: nowrap;
      transition: opacity .16s ease, transform .16s ease, width .16s ease, font-size .16s ease;
    }}
    article:hover .delete-card, .delete-card:focus-visible {{
      opacity: 1;
      transform: translateY(0);
    }}
    .delete-card.confirming {{
      width: 86px;
      padding: 0 10px;
      font-size: 12px;
      font-weight: 700;
      opacity: 1;
      transform: translateY(0);
    }}
    .favorite-card {{
      position: absolute;
      top: 10px;
      left: 10px;
      width: 34px;
      height: 34px;
      border: 1px solid rgba(23, 32, 27, 0.12);
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.94);
      color: #6b756f;
      font-size: 21px;
      line-height: 1;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 8px 22px rgba(23, 32, 27, 0.12);
      opacity: 0;
      transform: translateY(-4px);
      transition: opacity .16s ease, transform .16s ease, background .16s ease, color .16s ease;
    }}
    article:hover .favorite-card,
    .favorite-card:focus-visible,
    .favorite-card.is-favorite {{
      opacity: 1;
      transform: translateY(0);
    }}
    .favorite-card.is-favorite {{
      background: #f3b94b;
      color: #17201b;
      border-color: #e5aa36;
    }}
    .favorite-card:disabled {{
      cursor: wait;
      opacity: 0.7;
    }}
    article.is-deleting {{
      opacity: 0.5;
      pointer-events: none;
    }}
    .body {{
      padding: 12px 12px 14px;
      display: flex;
      gap: 10px;
      flex-direction: column;
      flex: 1;
    }}
    .category {{
      color: var(--accent-2);
      font-size: 12px;
      font-weight: 700;
    }}
    h2 {{
      margin: 0;
      font-size: 15px;
      line-height: 1.32;
      letter-spacing: 0;
    }}
    .meta {{
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
    }}
    .desc {{
      color: #36443b;
      font-size: 13px;
      line-height: 1.45;
    }}
    .tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
      margin-top: auto;
    }}
    .tag {{
      border-radius: 999px;
      background: #eef3ef;
      color: #4f5b54;
      padding: 4px 7px;
      font-size: 11px;
    }}
    .links {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }}
    .links a {{
      display: inline-flex;
      justify-content: center;
      align-items: center;
      min-height: 34px;
      border: 1px solid var(--line);
      border-radius: 6px;
      color: var(--ink);
      text-decoration: none;
      font-size: 12px;
      background: #fff;
    }}
    .links a:hover {{
      border-color: var(--accent);
      color: var(--accent);
    }}
    .empty {{
      display: none;
      padding: 40px 0;
      color: var(--muted);
      text-align: center;
      font-size: 15px;
    }}
    @media (max-width: 760px) {{
      .wrap {{ padding-left: 14px; padding-right: 14px; }}
      .title-row {{ display: block; }}
      .page-nav {{ justify-content: flex-start; margin-bottom: 8px; }}
      .toolbar {{ grid-template-columns: 1fr; }}
      .gallery {{ grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }}
      .favorite-card, .delete-card {{ opacity: 1; transform: translateY(0); }}
    }}
  </style>
</head>
<body data-page="{page_kind}">
  <header>
    <div class="wrap">
      <div class="title-row">
        <div>
          <h1>{page_title}</h1>
          <div class="subtitle stats">
            <span><strong id="visible-count">{s["images"]}</strong> / {s["images"]} {count_label}</span>
            <span><strong>{s["products"]}</strong> 个产品页</span>
          </div>
        </div>
        {nav}
      </div>
      <div class="toolbar">
        <input id="search" type="search" placeholder="搜索：HDPE、poly lumber、recycled plastic、Loll、POLYWOOD、Winawood...">
        <button class="reset" id="reset">清空筛选</button>
      </div>
      <div class="filters" aria-label="按结构分类筛选">
        {category_buttons}
      </div>
      <div class="note">
        当前只保留 HDPE / PE / poly lumber / recycled plastic 方向的单把完整扶手椅产品图；不保留铝合金、金属、木材、藤编/绳编/织带、PP 树脂、一体注塑、Adirondack 大斜背、无扶手、场景图、局部图和多椅组合。同一款式的不同颜色只显示一张代表图；每张卡片都有产品名、材料/结构说明、来源、产品页链接和原图链接。
      </div>
    </div>
  </header>
  <main class="wrap">
    <section class="gallery" id="gallery">
      {cards}
    </section>
    <div class="empty" id="empty">{empty_text}</div>
  </main>
  <script>
    const pageKind = document.body.dataset.page || 'index';
    const favoriteStorageKey = 'productReferenceFavorites';
    const search = document.getElementById('search');
    const reset = document.getElementById('reset');
    let cards = Array.from(document.querySelectorAll('article[data-text]'));
    const visibleCount = document.getElementById('visible-count');
    const favoriteCount = document.getElementById('favorite-count');
    const empty = document.getElementById('empty');
    let activeCategory = '';
    let pendingDeleteButton = null;
    let pendingDeleteTimer = 0;
    let favoriteTotal = favoriteCount ? Number(favoriteCount.dataset.count || favoriteCount.textContent || '0') : 0;

    function readStoredFavorites() {{
      try {{
        return new Set(JSON.parse(localStorage.getItem(favoriteStorageKey) || '[]'));
      }} catch (error) {{
        return new Set();
      }}
    }}

    function writeStoredFavorites(ids) {{
      localStorage.setItem(favoriteStorageKey, JSON.stringify(Array.from(ids).sort()));
    }}

    let storedFavorites = readStoredFavorites();

    function applyFilters() {{
      const q = search.value.trim().toLowerCase();
      let shown = 0;
      for (const card of cards) {{
        const text = card.dataset.text || '';
        const category = card.dataset.category || '';
        const okSearch = !q || text.includes(q);
        const okCategory = !activeCategory || category === activeCategory;
        const okFavorite = pageKind !== 'favorites' || card.dataset.favorite === '1';
        const show = okSearch && okCategory && okFavorite;
        card.style.display = show ? '' : 'none';
        if (show) shown++;
      }}
      visibleCount.textContent = shown;
      empty.style.display = shown ? 'none' : 'block';
    }}

    document.querySelectorAll('.chip').forEach((button) => {{
      button.addEventListener('click', () => {{
        activeCategory = activeCategory === button.dataset.filter ? '' : button.dataset.filter;
        document.querySelectorAll('.chip').forEach((b) => b.classList.toggle('active', b === button && activeCategory));
        applyFilters();
      }});
    }});

    search.addEventListener('input', applyFilters);
    reset.addEventListener('click', () => {{
      search.value = '';
      activeCategory = '';
      document.querySelectorAll('.chip.active').forEach((b) => b.classList.remove('active'));
      applyFilters();
    }});

    function setFavoriteButton(button, isFavorite) {{
      button.classList.toggle('is-favorite', isFavorite);
      button.textContent = isFavorite ? '★' : '☆';
      const label = isFavorite ? '取消收藏' : '收藏';
      button.title = label;
      button.setAttribute('aria-label', label);
      const card = button.closest('article');
      if (card) card.dataset.favorite = isFavorite ? '1' : '0';
    }}

    function setFavoriteCount(value) {{
      favoriteTotal = Math.max(0, Number(value) || 0);
      if (!favoriteCount) return;
      favoriteCount.textContent = favoriteTotal;
      favoriteCount.dataset.count = String(favoriteTotal);
    }}

    function updateStoredFavorite(id, isFavorite) {{
      if (isFavorite) storedFavorites.add(id);
      else storedFavorites.delete(id);
      writeStoredFavorites(storedFavorites);
      setFavoriteCount(storedFavorites.size);
    }}

    function applyStoredFavorites() {{
      for (const button of document.querySelectorAll('.favorite-card')) {{
        const card = button.closest('article');
        if (!card) continue;
        const id = card.dataset.id;
        if (button.classList.contains('is-favorite')) storedFavorites.add(id);
        if (storedFavorites.has(id)) setFavoriteButton(button, true);
      }}
      writeStoredFavorites(storedFavorites);
      if (storedFavorites.size) setFavoriteCount(storedFavorites.size);
    }}

    async function toggleFavorite(button) {{
      const card = button.closest('article');
      if (!card) return;
      const id = card.dataset.id;
      const nextFavorite = !button.classList.contains('is-favorite');
      button.disabled = true;
      try {{
        const response = await fetch('/api/favorite', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ id, favorite: nextFavorite }})
        }});
        if (!response.ok) throw new Error(await response.text());
        const result = await response.json();
        setFavoriteButton(button, Boolean(result.favorite));
        setFavoriteCount(result.favorite_count);
        updateStoredFavorite(id, Boolean(result.favorite));
        if (pageKind === 'favorites' && !result.favorite) {{
          applyFilters();
        }}
      }} catch (error) {{
        setFavoriteButton(button, nextFavorite);
        updateStoredFavorite(id, nextFavorite);
        if (pageKind === 'favorites' && !nextFavorite) applyFilters();
      }} finally {{
        button.disabled = false;
      }}
    }}

    document.querySelectorAll('.favorite-card').forEach((button) => {{
      button.addEventListener('click', (event) => {{
        event.preventDefault();
        event.stopPropagation();
        toggleFavorite(button);
      }});
    }});

    function resetDeleteButton(button) {{
      if (!button) return;
      button.dataset.confirm = '';
      button.classList.remove('confirming');
      button.textContent = '×';
      button.title = '删除这张参考图';
      button.setAttribute('aria-label', '删除这张参考图');
      if (pendingDeleteButton === button) pendingDeleteButton = null;
    }}

    function resetPendingDelete(exceptButton = null) {{
      if (pendingDeleteTimer) {{
        clearTimeout(pendingDeleteTimer);
        pendingDeleteTimer = 0;
      }}
      if (pendingDeleteButton && pendingDeleteButton !== exceptButton) {{
        resetDeleteButton(pendingDeleteButton);
      }}
    }}

    async function deleteCard(button) {{
      const card = button.closest('article');
      if (!card) return;
      resetPendingDelete(button);
      const id = card.dataset.id;
      button.disabled = true;
      button.textContent = '删除中';
      card.classList.add('is-deleting');
      try {{
        const response = await fetch('/api/delete', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ id }})
        }});
        if (!response.ok) throw new Error(await response.text());
        card.remove();
        cards = Array.from(document.querySelectorAll('article[data-text]'));
        resetPendingDelete();
        applyFilters();
        window.location.reload();
      }} catch (error) {{
        alert(`删除失败：${{error.message || error}}`);
        card.classList.remove('is-deleting');
        button.disabled = false;
        resetDeleteButton(button);
      }}
    }}

    document.querySelectorAll('.delete-card').forEach((button) => {{
      button.addEventListener('click', (event) => {{
        event.preventDefault();
        event.stopPropagation();
        if (button.dataset.confirm === '1') {{
          deleteCard(button);
          return;
        }}
        resetPendingDelete(button);
        pendingDeleteButton = button;
        button.dataset.confirm = '1';
        button.classList.add('confirming');
        button.textContent = '确认删除';
        button.title = '再次点击确认删除';
        button.setAttribute('aria-label', '再次点击确认删除');
        pendingDeleteTimer = setTimeout(() => resetDeleteButton(button), 4000);
      }});
    }});

    document.addEventListener('click', (event) => {{
      if (!event.target.closest('.delete-card')) resetPendingDelete();
    }});

    applyStoredFavorites();
    applyFilters();
  </script>
</body>
</html>
"""
        return html_doc

    HTML_OUT.write_text(render_page(entries, "index"), encoding="utf-8")
    FAVORITES_HTML_OUT.write_text(render_page(entries, "favorites"), encoding="utf-8")


def card_html(entry: dict, favorites: set[str]) -> str:
    text = " ".join(
        [
            entry["title"],
            entry["source"],
            entry["category"],
            entry["trust"],
            entry.get("description", ""),
            " ".join(entry["tags"]),
        ]
    ).lower()
    tags = "".join(f'<span class="tag">{html.escape(tag)}</span>' for tag in entry["tags"])
    collapsed_count = int(entry.get("collapsed_count") or 1)
    merged_note = (
        f'<span class="tag">已合并 {collapsed_count} 张同款图</span>'
        if collapsed_count > 1
        else ""
    )
    is_favorite = entry["id"] in favorites
    favorite_class = "favorite-card is-favorite" if is_favorite else "favorite-card"
    favorite_label = "取消收藏" if is_favorite else "收藏"
    favorite_icon = "★" if is_favorite else "☆"
    favorite_data = "1" if is_favorite else "0"
    return f"""<article data-id="{html.escape(entry["id"])}" data-favorite="{favorite_data}" data-title="{html.escape(entry["title"])}" data-category="{html.escape(entry["category"])}" data-source="{html.escape(entry["source"])}" data-text="{html.escape(text)}">
    <a class="thumb" href="{html.escape(entry["product_url"])}" target="_blank" rel="noopener noreferrer">
    <img src="{html.escape(entry.get("thumb_url") or optimized_remote_preview(entry["image_url"]))}" alt="{html.escape(entry["title"])}" loading="lazy" decoding="async" referrerpolicy="no-referrer">
    <button class="{favorite_class}" type="button" title="{favorite_label}" aria-label="{favorite_label}">{favorite_icon}</button>
    <button class="delete-card" type="button" title="删除这张参考图" aria-label="删除这张参考图">×</button>
  </a>
  <div class="body">
    <div class="category">{html.escape(entry["category"])}</div>
    <h2>{html.escape(entry["title"])}</h2>
    <div class="meta">{html.escape(entry["source"])} · {html.escape(entry["trust"])}</div>
    <div class="desc">{html.escape(entry.get("description") or "真实户外椅产品图，可点产品页复核结构。")}</div>
    <div class="tags">{tags}{merged_note}</div>
    <div class="links">
      <a href="{html.escape(entry["product_url"])}" target="_blank" rel="noopener noreferrer">产品页</a>
      <a href="{html.escape(entry["image_url"])}" target="_blank" rel="noopener noreferrer">打开图片</a>
    </div>
  </div>
</article>"""


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    products: list[Product] = []

    log("Collecting Shopify product images...")
    for source in SHOPIFY_SOURCES:
        log(f"- {source['name']}")
        before = len(products)
        products.extend(collect_shopify_products(source))
        log(f"  + {len(products) - before} products")

    log("Collecting sitemap product pages...")
    for source in SITEMAP_SOURCES:
        log(f"- {source['name']}")
        before = len(products)
        products.extend(collect_sitemap_products(source))
        log(f"  + {len(products) - before} products")

    log("Collecting manual seed pages...")
    seen_product_urls = {p.url for p in products}
    for seed in SEED_PAGES:
        if seed["url"] in seen_product_urls:
            continue
        product = extract_shopify_seed_product(
            seed["source"],
            seed["url"],
            seed["category"],
            seed["trust"],
            max_images=12,
        ) or extract_page_product(
            seed["source"],
            seed["url"],
            seed["category"],
            seed["trust"],
            max_images=12,
        )
        if product:
            products.append(product)
            seen_product_urls.add(seed["url"])
            log(f"  + {seed['source']}: {product.title} ({len(product.images)} images)")

    entries = flatten_products(products)
    entries.sort(key=lambda item: (item["category"], item["source"], item["title"], item["id"]))

    write_json(entries)
    write_csv(entries)
    write_html(entries)

    s = stats(entries)
    log("")
    log(f"Done: {s['images']} images from {s['products']} product pages.")
    log(f"HTML: {HTML_OUT}")
    log(f"JSON: {JSON_OUT}")
    log(f"CSV:  {CSV_OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
