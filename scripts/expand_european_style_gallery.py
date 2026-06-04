#!/usr/bin/env python3
"""Add European outdoor chair styles to the local gallery, one card per style."""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import build_real_reference_gallery as gallery


ROOT = Path(__file__).resolve().parents[1]
GALLERY_DIR = ROOT / "reference_gallery"
JSON_PATH = GALLERY_DIR / "images.json"
EUROPE_BACKUP = GALLERY_DIR / "images_before_europe_expansion.json"

CONNOX_SITEMAPS = ["https://www.connox.com/sitemap-7.xml"]

EUROPEAN_MANUAL_SEEDS = [
    {
        "url": "https://www.tdp.co.uk/product/cromford-recycled-plastic-garden-chairs/",
        "source": "TDP",
        "category": "EU | 欧洲再生塑料/板条主参考",
        "trust": "UK recycled plastic furniture",
    },
    {
        "url": "https://www.tdp.co.uk/product/belper-chair/",
        "source": "TDP",
        "category": "EU | 欧洲再生塑料/板条主参考",
        "trust": "UK recycled plastic furniture",
    },
    {
        "url": "https://www.funkihomes.com/garden-chairs/9179-67762-jude-recycled-plastic-garden-armchair",
        "source": "Funki Homes",
        "category": "EU | 欧洲再生塑料/板条主参考",
        "trust": "UK retailer: recycled plastic garden armchair",
    },
    {
        "url": "https://www.finnishdesignshop.com/en-us/product/remind-3735r-armchair-recycled-plastic-grey",
        "source": "Finnish Design Shop / Pedrali",
        "category": "EU | 欧洲再生塑料/PP设计款",
        "trust": "European design retail: Pedrali recycled plastic armchair",
    },
    {
        "url": "https://www.finnishdesignshop.com/en-us/product/rely-outdoor-hw70-chair-black",
        "source": "Finnish Design Shop / &Tradition",
        "category": "EU | 欧洲再生塑料/PP设计款",
        "trust": "European design retail: recycled PP outdoor chair",
    },
    {
        "url": "https://www.finnishdesignshop.com/en-us/product/palissade-armchair-sky-grey",
        "source": "Finnish Design Shop / HAY",
        "category": "EU | 欧洲板条/可转化风格",
        "trust": "European design retail: HAY slatted outdoor armchair",
    },
    {
        "url": "https://www.finnishdesignshop.com/en-us/product/traverse-armchair-heat-treated-oiled-ash",
        "source": "Finnish Design Shop / HAY",
        "category": "EU | 欧洲板条/可转化风格",
        "trust": "European design retail: HAY slatted outdoor armchair",
    },
    {
        "url": "https://www.vondom.com/us/products/chairs-ibiza-armchair-eugeni-quitllet-65041/",
        "source": "Vondom",
        "category": "EU | 欧洲再生塑料/PP设计款",
        "trust": "Spanish outdoor design brand",
    },
    {
        "url": "https://www.vondom.com/products/revolution-chairs-ibiza-chair-with-arms-eugeni-quitllet-65044",
        "source": "Vondom",
        "category": "EU | 欧洲再生塑料/PP设计款",
        "trust": "Spanish outdoor design brand",
    },
    {
        "url": "https://www.vondom.com/us/products/love-chair",
        "source": "Vondom",
        "category": "EU | 欧洲再生塑料/PP设计款",
        "trust": "Spanish outdoor design brand",
    },
    {
        "url": "https://www.vondom.com/products/chairs-wall-street-chair-eugeni-quitllet-65006",
        "source": "Vondom",
        "category": "EU | 欧洲再生塑料/PP设计款",
        "trust": "Spanish outdoor design brand",
    },
]

SLUG_EXCLUDE = re.compile(
    r"(stool|lounge|deck|folding|sofa|bench|pouf|rocking|hammock|sun|"
    r"lounger|rope|cord|weave|wicker|rattan|director|beanbag|cushion|"
    r"bar|counter|set|module|modular|kids|children|bistro|pool|daybed|"
    r"ottoman|replacement|tavolino|side-table|table)",
    re.I,
)

TEXT_EXCLUDE = re.compile(
    r"\b(folding|foldable|rattan|wicker|rope|cord|woven|weave|sun lounger|"
    r"chaise|daybed|stool|ottoman|bench|sofa|pouf|bar stool|counter stool)\b",
    re.I,
)

CONNOX_BRANDS = re.compile(
    r"/(audo|blomus|cane-line|carl-hansen|emu|fermob|fritz-hansen|hay|"
    r"houe|kartell|muuto|nardi|pedrali|skagerak|tiptoe|tradition|vondom|"
    r"vitra|petite-friture)-",
    re.I,
)

SOURCE_LABELS = {
    "audo": "Audo",
    "blomus": "Blomus",
    "cane-line": "Cane-line",
    "carl-hansen": "Carl Hansen & Son",
    "emu": "EMU",
    "fermob": "Fermob",
    "fritz-hansen": "Fritz Hansen / Skagerak",
    "hay": "HAY",
    "houe": "HOUE",
    "kartell": "Kartell",
    "muuto": "Muuto",
    "nardi": "Nardi",
    "pedrali": "Pedrali",
    "skagerak": "Skagerak",
    "tiptoe": "TipToe",
    "tradition": "&Tradition",
    "vondom": "Vondom",
    "vitra": "Vitra",
    "petite-friture": "Petite Friture",
}


def style_key(entry: dict) -> str:
    title = re.sub(r"\b(refurbished|yard sale)\b", "", entry.get("title", ""), flags=re.I)
    title = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
    return f"{entry.get('source', '').lower()}::{title}"


def source_from_url(url: str) -> str:
    match = CONNOX_BRANDS.search(url)
    if not match:
        return "European source"
    return SOURCE_LABELS.get(match.group(1).lower(), match.group(1).title())


def category_for_url(url: str, source: str) -> str:
    low = url.lower()
    if any(term in low for term in ("tdp", "winawood", "funkihomes", "reclip", "tiptoe", "audo", "muuto", "rely", "remind", "vondom")):
        return "EU | 欧洲再生塑料/PP设计款"
    if any(term in low for term in ("hay", "fermob", "houe", "emu", "thorvald", "tradition", "fritz-hansen", "carl-hansen")):
        return "EU | 欧洲板条/可转化风格"
    if source in {"Nardi", "Kartell"}:
        return "EU | 欧洲树脂/PP造型参考"
    return "EU | 欧洲户外椅风格补充"


def trust_for_source(source: str, url: str) -> str:
    low = url.lower()
    if "connox.com" in low:
        return f"Connox Europe: {source} outdoor chair product page"
    if "finnishdesignshop.com" in low:
        return f"Finnish Design Shop: {source} product page"
    return f"{source} product page"


def connox_candidates() -> list[str]:
    urls: list[str] = []
    for sitemap in CONNOX_SITEMAPS:
        try:
            raw = gallery.fetch_text(sitemap, timeout=20, retries=0)
        except Exception:
            continue
        for url in re.findall(r"<loc>(.*?)</loc>", raw):
            if "/categories/outdoor/garden-chairs/" not in url and "/categories/outdoor/outdoor-chairs-outdoor-benches/" not in url:
                continue
            if SLUG_EXCLUDE.search(url):
                continue
            if not CONNOX_BRANDS.search(url):
                continue
            if not re.search(r"(armchair|chair|stuhl)", url, re.I):
                continue
            urls.append(url)
    seen: set[str] = set()
    output: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            output.append(url)
            if len(output) >= 72:
                break
    print(f"Connox candidates: {len(output)}", flush=True)
    return output


def word_tokens(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]{3,}", text.lower())
    stop = {"outdoor", "garden", "chair", "armchair", "stuhl", "with", "from", "connox", "the"}
    return [word for word in words if word not in stop]


def score_image(url: str, title: str, source: str) -> int:
    low = url.lower()
    score = 0
    if "https://" in low.split("://", 1)[-1]:
        return -100
    if source.lower().replace("&", "").split()[0] in low:
        score += 20
    for token in word_tokens(title):
        if token in low:
            score += 6
    if any(term in low for term in ("situation", "ambiente", "outdoor", "garden", "terrace", "product")):
        score += 4
    if any(term in low for term in ("logo", "payment", "icon", "spare", "replacement", "table", "sofa", "bench", "stool", "pouf", "cushion")):
        score -= 30
    if any(term in low for term in ("jpg", "jpeg", "webp", "png")):
        score += 1
    return score


def extract_seed(seed: dict) -> dict | None:
    url = seed["url"]
    source = seed.get("source") or source_from_url(url)
    try:
        raw = gallery.fetch_text(url, timeout=10, retries=0)
    except Exception as exc:
        print(f"  ! fetch failed {url}: {exc}")
        return None
    parser = gallery.ImageHTMLParser(url)
    try:
        parser.feed(raw)
    except Exception:
        pass
    title = seed.get("title") or gallery.title_from_html(raw, parser) or source
    title = re.sub(r"\s*\|\s*Connox\s*$", "", title).strip()
    visible = re.sub(r"<[^>]+>", " ", raw[:160000])
    if TEXT_EXCLUDE.search(f"{title} {visible[:1000]}"):
        print(f"  - skipped excluded text: {title}")
        return None
    images = list(parser.images)
    for match in gallery.IMAGE_URL_RE.finditer(raw):
        images.append(gallery.normalize_url(match.group(0), url))
    images = gallery.unique_images(images, 30)
    ranked = sorted(images, key=lambda image: score_image(image, title, source), reverse=True)
    image_url = next((image for image in ranked if score_image(image, title, source) > -20), "")
    if not image_url:
        print(f"  ! no usable image: {title}")
        return None
    slug = re.sub(r"[^a-z0-9]+", "-", f"eu-{source}-{title}".lower()).strip("-")
    text = f"{title} {visible[:2500]} {source}"
    return {
        "id": slug[:90],
        "title": title,
        "source": source,
        "product_url": url,
        "image_url": image_url,
        "thumb_url": "",
        "category": seed.get("category") or category_for_url(url, source),
        "trust": seed.get("trust") or trust_for_source(source, url),
        "description": gallery.clean_description(visible, 170) or gallery.fallback_description(title, text),
        "collapsed_count": 1,
        "tags": european_tags(url, title, source),
    }


def european_tags(url: str, title: str, source: str) -> list[str]:
    low = f"{url} {title} {source}".lower()
    tags = ["欧洲款式"]
    if any(term in low for term in ("recycled", "再生", "reclip", "audo", "muuto", "remind", "rely", "vondom", "tdp", "winawood")):
        tags.append("recycled / PP")
    if any(term in low for term in ("slat", "palissade", "click", "reclip", "alua", "luxembourg", "thorvald", "traverse")):
        tags.append("slatted / lamella")
    if any(term in low for term in ("armchair", "arm-chair", "armlehnstuhl")):
        tags.append("armchair")
    if source in {"HAY", "HOUE", "Audo", "Muuto", "Fermob", "&Tradition"}:
        tags.append("欧洲设计品牌")
    return tags


def normalize_existing(entry: dict) -> dict:
    entry = dict(entry)
    source = entry.get("source", "")
    if source in {"POLYWOOD", "Trex Outdoor Furniture", "highwood", "Loll Designs", "Sun Country Leisure"}:
        entry["category"] = "US | 美国/北美HDPE补充参考"
        tags = list(entry.get("tags") or [])
        if "北美补充" not in tags:
            tags.append("北美补充")
        entry["tags"] = tags
    elif source in {"Winawood", "TDP"}:
        entry["category"] = "EU | 欧洲再生塑料/板条主参考"
        tags = list(entry.get("tags") or [])
        if "欧洲款式" not in tags:
            tags.insert(0, "欧洲款式")
        entry["tags"] = tags
    elif source == "Terra Outdoor":
        entry["category"] = "EU | 欧洲板条/可转化风格"
        tags = list(entry.get("tags") or [])
        for tag in ("欧洲款式", "slatted / lamella"):
            if tag not in tags:
                tags.append(tag)
        entry["tags"] = tags
    entry.setdefault("collapsed_count", 1)
    entry.setdefault("thumb_url", "")
    return entry


def main() -> int:
    sys.path.insert(0, str(ROOT / "scripts"))
    entries = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    if not EUROPE_BACKUP.exists():
        EUROPE_BACKUP.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")

    merged: dict[str, dict] = {}
    for entry in entries:
        normalized = normalize_existing(entry)
        merged[style_key(normalized)] = normalized

    seeds = [{"url": url} for url in connox_candidates()]
    seeds.extend(EUROPEAN_MANUAL_SEEDS)

    added = 0
    for index, seed in enumerate(seeds, 1):
        print(f"[{index}/{len(seeds)}] {seed['url']}", flush=True)
        entry = extract_seed(seed)
        if not entry:
            continue
        key = style_key(entry)
        if key in merged:
            continue
        merged[key] = entry
        added += 1
        print(f"  + {added:02d} {entry['source']}: {entry['title']}")

    output = sorted(merged.values(), key=lambda item: (not item["category"].startswith("EU"), item["category"], item["source"], item["title"]))
    gallery.write_json(output)
    gallery.write_csv(output)
    gallery.write_html(output)
    print(f"Added {added} European style cards. Total cards: {len(output)}")
    print(f"HTML: {gallery.HTML_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
