#!/usr/bin/env python3
"""Add European outdoor chair styles from Archiproducts garden-chair category pages."""

from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError

import build_real_reference_gallery as gallery
from expand_archiproducts_european_gallery import fetch, model_key, parse_cards


ROOT = Path(__file__).resolve().parents[1]
GALLERY_DIR = ROOT / "reference_gallery"
JSON_PATH = GALLERY_DIR / "images.json"
BACKUP_PATH = GALLERY_DIR / "images_before_archiproducts_category_expansion.json"

CATEGORY_URLS = [
    "https://www.archiproducts.com/en/products/garden-chairs",
    *[f"https://www.archiproducts.com/en/products/garden-chairs/{page}" for page in range(2, 11)],
    "https://www.archiproducts.com/en/products/outdoor-chairs",
    *[f"https://www.archiproducts.com/en/products/outdoor-chairs/{page}" for page in range(2, 6)],
]

EUROPEAN_SOURCES = {
    "10Deka",
    "Actiu",
    "Adico",
    "Akula Living",
    "ALMA DESIGN",
    "AMPM",
    "Arper",
    "Artu",
    "Atmosphera",
    "B&B Italia Outdoor",
    "BertO",
    "BISTROMANIA",
    "Blomus",
    "Calma",
    "Cane-line",
    "Carl Hansen & Søn",
    "Cassina",
    "Connubia",
    "Diabla",
    "Domkapa",
    "Emu",
    "EMU",
    "Ethimo",
    "Ethnicraft",
    "EXPORMIM",
    "Exteta",
    "Fermob",
    "Fiam",
    "Fischer Möbel",
    "Forni",
    "GABER",
    "GANDIABLASCO",
    "GANSK",
    "Giorgetti",
    "Gloster",
    "Grythyttan Stålmöbler",
    "GUBI",
    "Hay",
    "HAY",
    "HOUE",
    "ISIMAR",
    "Jardinico",
    "Jati Kebon",
    "Kartell",
    "Kristalia",
    "Lapalma",
    "Luxy",
    "Magis",
    "MANUTTI",
    "MDF Italia",
    "Mindo",
    "Molteni & C.",
    "Muuto",
    "Nardi",
    "Normann Copenhagen",
    "Paola Lenti",
    "Pedrali",
    "Plank",
    "Plust",
    "Poliform",
    "Potocco",
    "REDI Mobiliário",
    "RODA",
    "Royal Botania",
    "S-CAB",
    "SCAB DESIGN",
    "Seóra",
    "Serralunga",
    "Skargaarden",
    "SLIDE",
    "SUGIYAMA",
    "Talenti",
    "Thonet",
    "TipToe",
    "Tom Dixon",
    "TRIBÙ",
    "Unopiù",
    "Varaschin",
    "Vermobil",
    "VINEKO",
    "Vondom",
    "Weltevree",
    "Woud",
    "Zavotti",
    "Zuiver",
    "&Tradition",
}


def entry_key(entry: dict) -> str:
    return entry.get("model_key") or model_key(entry.get("source", ""), entry.get("title", ""))


def normalize_card(card: dict) -> dict:
    card = dict(card)
    source = card.get("source", "")
    if source == "In Stock":
        # These are shop-stock mirrors of known brands and create duplicate clutter.
        card["skip"] = True
        return card
    card.setdefault("collapsed_count", 1)
    card["model_key"] = entry_key(card)
    return card


def main() -> int:
    entries = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    if not BACKUP_PATH.exists():
        BACKUP_PATH.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")

    keys = {entry_key(entry) for entry in entries}
    urls = {entry.get("product_url", "") for entry in entries}
    added: list[dict] = []

    for index, url in enumerate(CATEGORY_URLS, 1):
        print(f"[{index}/{len(CATEGORY_URLS)}] {url}", flush=True)
        try:
            raw = fetch(url, timeout=12)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            print(f"  ! {type(exc).__name__}: {exc}", flush=True)
            continue
        candidates = [normalize_card(card) for card in parse_cards(raw, url)]
        page_added = 0
        for card in candidates:
            if card.get("skip"):
                continue
            if card.get("source") not in EUROPEAN_SOURCES:
                continue
            key = entry_key(card)
            if key in keys or card.get("product_url") in urls:
                continue
            keys.add(key)
            urls.add(card["product_url"])
            entries.append(card)
            added.append(card)
            page_added += 1
        print(f"  + {page_added} new styles ({len(candidates)} candidates)", flush=True)
        time.sleep(1.0)
        if len(added) >= 90:
            break

    entries.sort(key=lambda item: (item["category"], item["source"], item["title"]))
    gallery.write_json(entries)
    gallery.write_csv(entries)
    gallery.write_html(entries)
    print(f"Added {len(added)} category European styles. Total cards: {len(entries)}")
    print(f"HTML: {gallery.HTML_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
