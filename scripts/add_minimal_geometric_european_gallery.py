#!/usr/bin/env python3
"""Add 50 minimal geometric European outdoor armchair references."""

from __future__ import annotations

import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import quote, urlparse, urlunparse

import build_real_reference_gallery as gallery
from expand_archiproducts_category_gallery import (
    CATEGORY_URLS,
    EUROPEAN_SOURCES,
    normalize_card,
)
from expand_archiproducts_european_gallery import BRAND_SLUGS, fetch, model_key, parse_cards


ROOT = Path(__file__).resolve().parents[1]
GALLERY_DIR = ROOT / "reference_gallery"
JSON_PATH = GALLERY_DIR / "images.json"
HISTORY_PATH = GALLERY_DIR / "images_with_north_america_supplement.json"
BACKUP_PATH = GALLERY_DIR / "images_before_minimal_geometric_european_expansion.json"
REVIEW_PATH = GALLERY_DIR / "minimal_geometric_european_review.json"

HDPE_CATEGORY = "HDPE / PE 板件可转化"
EU_CATEGORY = "极简几何欧洲款式"
TARGET_COUNT = 50
SOURCE_LIMIT = 6
MANUAL_REJECT_IDS = {
    "eu-minimal-tradition-tradition-thorvald-sc95-outdoor-armchair",
    "eu-minimal-hay-hay-palissade-armchair-anthracite",
    "eu-minimal-hay-hay-traverse-outdoor-armchair",
    "eu-minimal-kartell-kartell-hiray-armchair",
    "eu-minimal-nardi-nardi-cassia-armchair",
    "eu-minimal-nardi-nardi-doga-relax-garden-armchair",
    "eu-minimal-nardi-nardi-komodo-poltrona-armchair",
    "eu-minimal-nardi-nardi-net-relax-armchair",
    "eu-minimal-nardi-nardi-net-armchair",
    "eu-minimal-blomus-blomus-yua-wire-outdoor-armchair",
    "eu-minimal-emu-emu-darwin-armchair",
    "eu-minimal-emu-emu-miky-armchair",
    "eu-minimal-emu-emu-mom-armchair",
    "eu-minimal-emu-emu-rio-r50-armchair",
    "eu-minimal-emu-emu-ronda-xs-armchair",
    "eu-minimal-emu-emu-twins-garden-armchair",
    "eu-minimal-carl-hansen-son-carl-hansen-ah502-garden-arm-chair",
    "eu-minimal-fermob-fermob-cadiz",
    "eu-minimal-terra-outdoor-reclips-dining-arm-chair-black-bamboo",
    "eu-minimal-s-cab-s-cab-koala",
    "eu-minimal-trib-trib-nomad",
    "eu-minimal-trib-trib-ukiyo",
    "eu-minimal-roda-roda-piper-021",
    "eu-minimal-ethimo-ethimo-patio",
}

ARM_TERMS = re.compile(
    r"\b(armchair|arm\s+chair|with\s+arms|with\s+armrests?|armrests?|"
    r"armlehnstuhl|poltrona|扶手)\b",
    re.I,
)
TITLE_REJECT = re.compile(r"\b(side\s+chair|side\s+stuhl|armless|without\s+arms?)\b", re.I)
TEXT_REJECT = re.compile(
    r"\b("
    r"sofa|sectional|loveseat|bench|stool|pouf|ottoman|sun\s*lounger|lounger|"
    r"chaise|daybed|bed|hammock|swing|rocking|rocker|recliner|folding|foldable|"
    r"bar\s+stool|counter|bar\s+chair|high\s+stool|table|side\s+table|cabinet|"
    r"lamp|cushion|cover|pillow|parasol|umbrella|fabric\s+pouf|beanbag|"
    r"fabric|sunbrella|rattan|wicker|woven|weave|rope|cord|cane|director|"
    r"castors|one\s+armrest|central\s+element|corner\s+element|end\s+element|"
    r"upholstered|bistro"
    r")\b",
    re.I,
)
STYLE_TERMS = re.compile(
    r"\b("
    r"outdoor|garden|terrace|patio|minimal|geometric|plastic|polypropylene|"
    r"resin|metal|steel|aluminium|aluminum|slat|slatted|mesh|wire|recycled|"
    r"armchair|armrests"
    r")\b",
    re.I,
)


PREFERRED_SOURCES = {
    "Audo": 120,
    "Muuto": 118,
    "&Tradition": 116,
    "HAY": 114,
    "Hay": 114,
    "HOUE": 112,
    "Pedrali": 110,
    "Kartell": 108,
    "Nardi": 106,
    "Vondom": 104,
    "EMU": 102,
    "Emu": 102,
    "Fermob": 100,
    "S-CAB": 98,
    "Magis": 96,
    "Kristalia": 94,
    "Blomus": 92,
    "Cane-line": 90,
    "TipToe": 88,
    "Carl Hansen & Son": 86,
    "Carl Hansen": 86,
    "Tom Dixon": 84,
    "Royal Botania": 82,
    "TRIBÙ": 80,
    "RODA": 78,
    "Ethimo": 76,
    "Talenti": 74,
    "Unopiù": 72,
    "Winawood": 70,
    "TDP": 68,
}


def source_label(source: str) -> str:
    aliases = {
        "Hay": "HAY",
        "Emu": "EMU",
        "Carl Hansen": "Carl Hansen & Son",
        "& Tradition": "&Tradition",
    }
    return aliases.get(source.strip(), source.strip())


def encode_url_path(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return url
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            quote(parsed.path, safe="/%:@"),
            "",
            parsed.query,
            parsed.fragment,
        )
    )


def text_for(entry: dict) -> str:
    return " ".join(
        str(part)
        for part in (
            entry.get("title", ""),
            entry.get("source", ""),
            entry.get("description", ""),
            entry.get("trust", ""),
            entry.get("product_url", ""),
            " ".join(entry.get("tags") or []),
        )
    )


def is_armchair_candidate(entry: dict) -> bool:
    title = entry.get("title", "")
    text = text_for(entry)
    if TITLE_REJECT.search(title):
        return False
    if TEXT_REJECT.search(text):
        return False
    return bool(ARM_TERMS.search(text))


def stable_key(entry: dict) -> str:
    source = source_label(entry.get("source", ""))
    title = entry.get("title", "")
    return entry.get("model_key") or model_key(source, title)


def material_tags(entry: dict) -> list[str]:
    low = text_for(entry).lower()
    tags = ["欧洲款式", "极简几何", "扶手椅"]
    if any(term in low for term in ("polypropylene", "resin", "plastic", "technopolymer", "pp")):
        tags.append("PP / resin")
    if any(term in low for term in ("recycled", "recyclable", "reclip", "再生")):
        tags.append("recycled")
    if any(term in low for term in ("metal", "steel", "aluminium", "aluminum", "wire", "mesh")):
        tags.append("metal frame")
    if any(term in low for term in ("slat", "slatted", "lamella", "wood", "teak")):
        tags.append("slatted")
    if any(term in low for term in ("archiproducts", "connox", "finnish design shop")):
        tags.append("欧洲零售/平台")
    if source_label(entry.get("source", "")) in PREFERRED_SOURCES:
        tags.append("欧洲设计品牌")
    return list(dict.fromkeys(tags))


def normalize_entry(entry: dict, origin: str) -> dict:
    normalized = dict(entry)
    normalized["source"] = source_label(normalized.get("source", ""))
    normalized["image_url"] = encode_url_path(normalized.get("image_url", ""))
    normalized["product_url"] = encode_url_path(normalized.get("product_url", ""))
    normalized["category"] = EU_CATEGORY
    normalized["id"] = re.sub(
        r"[^a-z0-9]+",
        "-",
        f"eu-minimal-{normalized['source']}-{normalized.get('title', '')}".lower(),
    ).strip("-")[:96]
    normalized["thumb_url"] = ""
    normalized["tags"] = material_tags(normalized)
    normalized["collapsed_count"] = normalized.get("collapsed_count") or 1
    normalized["model_key"] = stable_key(normalized)
    if origin == "history":
        normalized["trust"] = normalized.get("trust") or f"{normalized['source']} product page"
    else:
        normalized["trust"] = normalized.get("trust") or f"Archiproducts Europe: {normalized['source']} product page"
    if not normalized.get("description"):
        normalized["description"] = "欧洲极简几何户外扶手椅真实产品图；作为 HDPE / PE 板件造型转化参考。"
    return normalized


def score(entry: dict, origin: str) -> int:
    source = source_label(entry.get("source", ""))
    text = text_for(entry).lower()
    value = PREFERRED_SOURCES.get(source, 55)
    if origin == "history":
        value += 22
    if "armchair" in text or "arm chair" in text:
        value += 10
    if any(term in text for term in ("minimal", "geometric", "mesh", "wire", "slat", "palissade", "reclip")):
        value += 8
    if any(term in text for term in ("plastic", "polypropylene", "resin", "recycled")):
        value += 4
    if source in {"EMU", "Nardi", "HOUE"}:
        value -= 2
    return value


def history_candidates() -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    return [
        normalize_entry(entry, "history")
        for entry in data
        if entry.get("category", "").startswith("EU") and is_armchair_candidate(entry)
    ]


def archiproducts_candidates() -> list[dict]:
    candidates: list[dict] = []
    seen_urls: set[str] = set()

    urls = CATEGORY_URLS[:10]
    for index, url in enumerate(urls, 1):
        print(f"[category {index}/{len(urls)}] {url}", flush=True)
        try:
            raw = fetch(url, timeout=12)
        except Exception as exc:
            print(f"  ! {type(exc).__name__}: {exc}", flush=True)
            continue
        for card in [normalize_card(card) for card in parse_cards(raw, url)]:
            if card.get("skip"):
                continue
            if card.get("source") not in EUROPEAN_SOURCES:
                continue
            if card.get("product_url") in seen_urls:
                continue
            if not is_armchair_candidate(card):
                continue
            if not STYLE_TERMS.search(text_for(card)):
                continue
            seen_urls.add(card.get("product_url", ""))
            candidates.append(normalize_entry(card, "archiproducts-category"))
        time.sleep(0.7)

    if len(candidates) < 60:
        for index, brand in enumerate(BRAND_SLUGS, 1):
            url = f"https://www.archiproducts.com/en/{brand}"
            print(f"[brand {index}/{len(BRAND_SLUGS)}] {url}", flush=True)
            try:
                raw = fetch(url, timeout=10)
            except Exception as exc:
                print(f"  ! {type(exc).__name__}: {exc}", flush=True)
                continue
            for card in parse_cards(raw, url):
                if card.get("product_url") in seen_urls:
                    continue
                if not is_armchair_candidate(card):
                    continue
                if not STYLE_TERMS.search(text_for(card)):
                    continue
                seen_urls.add(card.get("product_url", ""))
                candidates.append(normalize_entry(card, "archiproducts-brand"))
            time.sleep(0.7)
            if len(candidates) >= 80:
                break
    return candidates


def select_candidates(candidates: list[tuple[str, dict]]) -> tuple[list[dict], list[dict]]:
    selected: list[dict] = []
    rejected: list[dict] = []
    source_counts: Counter[str] = Counter()
    keys: set[str] = set()
    urls: set[str] = set()

    ranked = sorted(candidates, key=lambda pair: score(pair[1], pair[0]), reverse=True)
    for origin, entry in ranked:
        source = source_label(entry.get("source", ""))
        key = stable_key(entry)
        reason = ""
        if entry.get("id") in MANUAL_REJECT_IDS:
            reason = "manual visual reject: scene/multi-product/detail/lounge-like"
        elif key in keys or entry.get("product_url") in urls:
            reason = "duplicate model or product URL"
        elif source_counts[source] >= SOURCE_LIMIT:
            reason = f"source limit {SOURCE_LIMIT}"
        elif not is_armchair_candidate(entry):
            reason = "not a strict armchair candidate"
        if reason:
            rejected.append(
                {
                    "id": entry.get("id"),
                    "title": entry.get("title"),
                    "source": source,
                    "origin": origin,
                    "reason": reason,
                }
            )
            continue
        selected.append(entry)
        source_counts[source] += 1
        keys.add(key)
        urls.add(entry.get("product_url", ""))
        if len(selected) == TARGET_COUNT:
            break
    return selected, rejected


def main() -> int:
    current = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    if not BACKUP_PATH.exists():
        BACKUP_PATH.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")

    base_entries = [entry for entry in current if entry.get("category") == HDPE_CATEGORY]
    if len(base_entries) != 99:
        print(f"Expected 99 HDPE entries, found {len(base_entries)}", file=sys.stderr)
        return 1

    candidate_pairs: list[tuple[str, dict]] = []
    history = history_candidates()
    print(f"history candidates: {len(history)}", flush=True)
    candidate_pairs.extend(("history", entry) for entry in history)

    arch = archiproducts_candidates()
    print(f"archiproducts candidates: {len(arch)}", flush=True)
    candidate_pairs.extend(("archiproducts", entry) for entry in arch)

    selected, rejected = select_candidates(candidate_pairs)
    if len(selected) < TARGET_COUNT:
        print(f"Only selected {len(selected)} candidates; target is {TARGET_COUNT}", file=sys.stderr)
        return 2

    output = base_entries + selected
    gallery.write_json(output)
    gallery.write_csv(output)
    gallery.write_html(output)

    review = {
        "category": EU_CATEGORY,
        "target_count": TARGET_COUNT,
        "selected_count": len(selected),
        "source_counts": Counter(entry["source"] for entry in selected),
        "selected": [
            {
                "index": index,
                "id": entry["id"],
                "title": entry["title"],
                "source": entry["source"],
                "product_url": entry["product_url"],
                "image_url": entry["image_url"],
            }
            for index, entry in enumerate(selected, 1)
        ],
        "rejected_sample": rejected[:120],
    }
    REVIEW_PATH.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Selected {len(selected)} minimal geometric European armchairs.")
    print("Sources:", dict(Counter(entry["source"] for entry in selected)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
