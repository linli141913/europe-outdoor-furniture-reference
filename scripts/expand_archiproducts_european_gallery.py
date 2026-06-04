#!/usr/bin/env python3
"""Add more European outdoor chair styles from Archiproducts brand pages."""

from __future__ import annotations

import html
import json
import re
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

import build_real_reference_gallery as gallery


ROOT = Path(__file__).resolve().parents[1]
GALLERY_DIR = ROOT / "reference_gallery"
JSON_PATH = GALLERY_DIR / "images.json"
BACKUP_PATH = GALLERY_DIR / "images_before_archiproducts_expansion.json"

BRAND_SLUGS = [
    "emu",
    "nardi",
    "pedrali",
    "fast",
    "fermob",
    "vondom",
    "kartell",
    "magis",
    "driade",
    "ethimo",
    "tribu",
    "varaschin",
    "gandia-blasco",
    "kettal",
    "hay",
    "muuto",
    "houe",
    "cane-line",
    "blomus",
    "carl-hansen-son",
    "fritz-hansen",
    "normann-copenhagen",
    "gubi",
    "lapalma",
    "mdf-italia",
    "kristalia",
    "plust",
    "slide",
    "arrmet",
    "ligne-roset",
    "expormim",
    "diabla",
    "skapin",
    "mara",
    "lapalma",
    "talenti",
    "roda",
    "royal-botania",
    "extremis",
    "manutti",
    "b-b-italia-outdoor",
    "desalto",
    "infiniti",
    "scab-design",
    "connubia",
    "gaber",
    "midj",
    "s-cab",
    "mindo",
    "serax",
    "weltevree",
    "ferm-living",
    "house-doctor",
    "jan-kurtz",
    "grythyttan",
    "vermobil",
    "zuiver",
    "tom-dixon",
    "tiptoe",
    "nine",
    "woud",
    "out-objekte-unserer-tage",
    "fdb-mobler",
]

EXCLUDE = re.compile(
    r"\b("
    r"sofa|sectional|loveseat|bench|stool|pouf|ottoman|sun\s*lounger|lounger|"
    r"chaise|daybed|bed|hammock|swing|rocking|rocker|recliner|folding|foldable|"
    r"bar\s+stool|counter|bar\s+chair|high\s+stool|table|side\s+table|cabinet|"
    r"lamp|cushion|cover|pillow|parasol|umbrella|fabric\s+pouf|beanbag|"
    r"fabric|sunbrella|synthetic\s+fibre|synthetic\s+fiber|fibre|fiber|"
    r"rattan|wicker|woven|weave|rope|cord|cane|director|castors|one\s+armrest|"
    r"central\s+element|corner\s+element|end\s+element|upholstered"
    r")\b",
    re.I,
)

INCLUDE = re.compile(r"\b(chair|armchair|with armrests|garden chair|outdoor chair)\b", re.I)
OUTDOOR = re.compile(r"\b(outdoor|garden|patio|terrace|exterior)\b", re.I)

COMMON_MODEL_WORDS = {
    "and",
    "the",
    "with",
    "chair",
    "chairs",
    "armchair",
    "armchairs",
    "garden",
    "outdoor",
    "patio",
    "terrace",
    "dining",
    "side",
    "arm",
    "arms",
    "armrests",
    "plastic",
    "metal",
    "steel",
    "aluminium",
    "aluminum",
    "polypropylene",
    "resin",
    "wood",
    "wooden",
    "teak",
    "stackable",
    "stapelbarer",
    "stuhl",
    "armlehnstuhl",
    "chaise",
}


def fetch(url: str, timeout: int = 9) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": gallery.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urlopen(req, timeout=timeout) as response:
        return response.read().decode(response.headers.get_content_charset() or "utf-8", "ignore")


def source_key(source: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "", source.lower())
    aliases = {
        "emU".lower(): "emu",
        "carlhansenson": "carlhansen",
        "carlhansen": "carlhansen",
        "fritzhansenskagerak": "fritzhansen",
        "tradition": "tradition",
        "andtradition": "tradition",
    }
    return aliases.get(key, key)


def model_key(source: str, title: str, model: str = "") -> str:
    text = model or title
    text = re.sub(re.escape(source), " ", text, flags=re.I)
    tokens = [
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if token not in COMMON_MODEL_WORDS and len(token) > 1
    ]
    return f"{source_key(source)}::{('-'.join(tokens[:3]) or re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-'))}"


def category_for(desc: str, title: str) -> str:
    low = f"{desc} {title}".lower()
    if any(term in low for term in ("recycled", "recyclable", "recycled plastic")):
        return "EU | 欧洲再生塑料/PP设计款"
    if any(term in low for term in ("polypropylene", "resin", "plastic", "technopolymer", "polyethylene")):
        return "EU | 欧洲树脂/PP造型参考"
    if any(term in low for term in ("slat", "slatted", "lamella", "teak", "wood", "wooden")):
        return "EU | 欧洲板条/可转化风格"
    if any(term in low for term in ("steel", "aluminium", "aluminum", "metal", "galvanized")):
        return "EU | 欧洲金属/轻量庭院风格"
    return "EU | 欧洲户外椅风格补充"


def parse_cards(raw: str, brand_url: str) -> list[dict]:
    cards: list[dict] = []
    pattern = re.compile(
        r'<figure class="product" data-product="(.*?)">\s*'
        r'<a class="_search-item-anchor" href="([^"]+)" title="([^"]+)"[\s\S]*?'
        r'<img src="([^"]+)"(?:\s+srcset="([^"]+)")?',
        re.I,
    )
    for data_raw, href, title_attr, img_src, srcset in pattern.findall(raw):
        try:
            product_data = json.loads(html.unescape(data_raw))
        except json.JSONDecodeError:
            product_data = {}
        source = str(product_data.get("manufacturer") or "").strip()
        name = str(product_data.get("name") or "").strip()
        desc = str(product_data.get("desc") or html.unescape(title_attr)).strip()
        if not source or not name:
            continue
        full_text = f"{source} {name} {desc} {href}"
        if not INCLUDE.search(full_text):
            continue
        if not OUTDOOR.search(full_text):
            continue
        if EXCLUDE.search(full_text):
            continue
        image_url = best_image(img_src, srcset)
        product_url = urljoin("https://www.archiproducts.com", href)
        card_id = re.sub(r"[^a-z0-9]+", "-", f"archiproducts-{source}-{name}".lower()).strip("-")
        title = f"{source} - {name}"
        cards.append(
            {
                "id": card_id[:100],
                "title": title,
                "source": source,
                "product_url": product_url,
                "image_url": image_url,
                "thumb_url": "",
                "category": category_for(desc, title),
                "trust": f"Archiproducts Europe: {source} product page",
                "description": gallery.clean_description(desc, 165) or gallery.fallback_description(title, desc),
                "collapsed_count": 1,
                "tags": tags_for(desc, title),
                "model_key": model_key(source, title, name),
            }
        )
    return cards


def best_image(img_src: str, srcset: str) -> str:
    if not srcset:
        return html.unescape(img_src)
    candidates: list[tuple[int, str]] = []
    for part in html.unescape(srcset).split(","):
        pieces = part.strip().split()
        if not pieces:
            continue
        width = 0
        if len(pieces) > 1:
            match = re.search(r"(\d+)w", pieces[1])
            if match:
                width = int(match.group(1))
        candidates.append((width, pieces[0]))
    if not candidates:
        return html.unescape(img_src)
    return sorted(candidates, reverse=True)[0][1]


def tags_for(desc: str, title: str) -> list[str]:
    low = f"{desc} {title}".lower()
    tags = ["欧洲款式", "Archiproducts"]
    if any(term in low for term in ("polypropylene", "resin", "plastic", "technopolymer")):
        tags.append("PP / resin")
    if any(term in low for term in ("recycled", "recyclable")):
        tags.append("recycled")
    if any(term in low for term in ("slat", "wood", "teak")):
        tags.append("slatted / wood cue")
    if any(term in low for term in ("armrest", "armchair", "with arms")):
        tags.append("armchair")
    return tags


def existing_model_keys(entries: list[dict]) -> set[str]:
    keys: set[str] = set()
    for entry in entries:
        source = entry.get("source", "")
        title = entry.get("title", "")
        keys.add(entry.get("model_key") or model_key(source, title))
    return keys


def main() -> int:
    entries = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    if not BACKUP_PATH.exists():
        BACKUP_PATH.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")

    keys = existing_model_keys(entries)
    product_urls = {entry.get("product_url", "") for entry in entries}
    added: list[dict] = []

    seen_brand_slugs: set[str] = set()
    for index, brand in enumerate(BRAND_SLUGS, 1):
        if brand in seen_brand_slugs:
            continue
        seen_brand_slugs.add(brand)
        url = f"https://www.archiproducts.com/en/{brand}"
        print(f"[{index}/{len(BRAND_SLUGS)}] {url}", flush=True)
        try:
            raw = fetch(url)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            print(f"  ! {type(exc).__name__}: {exc}", flush=True)
            continue
        brand_cards = parse_cards(raw, url)
        brand_added = 0
        for card in brand_cards:
            key = card["model_key"]
            if key in keys or card["product_url"] in product_urls:
                continue
            keys.add(key)
            product_urls.add(card["product_url"])
            entries.append(card)
            added.append(card)
            brand_added += 1
        print(f"  + {brand_added} new styles ({len(brand_cards)} candidates)", flush=True)
        # Archiproducts requests a crawl delay; keep it civilized.
        time.sleep(1.2)
        if len(added) >= 120:
            break

    entries.sort(key=lambda item: (item["category"], item["source"], item["title"]))
    gallery.write_json(entries)
    gallery.write_csv(entries)
    gallery.write_html(entries)
    print(f"Added {len(added)} Archiproducts European styles. Total cards: {len(entries)}")
    print(f"HTML: {gallery.HTML_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
