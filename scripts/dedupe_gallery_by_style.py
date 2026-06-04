#!/usr/bin/env python3
"""Collapse the gallery from image-level cards to one representative per style."""

from __future__ import annotations

import json
import re
import shutil
from collections import defaultdict
from pathlib import Path

import build_real_reference_gallery as gallery


ROOT = Path(__file__).resolve().parents[1]
GALLERY_DIR = ROOT / "reference_gallery"
JSON_PATH = GALLERY_DIR / "images.json"
BACKUP_PATH = GALLERY_DIR / "images_all_variants.json"


def style_key(entry: dict) -> str:
    title = entry.get("title", "")
    title = re.sub(r"\brefurbished\b", "", title, flags=re.I)
    title = re.sub(r"\byard sale\b", "", title, flags=re.I)
    title = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
    return f"{entry.get('source', '').lower()}::{title}"


def representative_score(entry: dict) -> tuple[int, str]:
    image_url = (entry.get("image_url") or "").lower()
    title = (entry.get("title") or "").lower()
    score = 0
    if entry.get("thumb_url"):
        score += 20
    if "refurbished" not in title and "yard sale" not in title:
        score += 10
    if any(term in image_url for term in ("lifestyle", "hero", "outdoor", "patio")):
        score += 4
    if any(term in image_url for term in ("white", "transparent", "cutout")):
        score += 2
    # Keep ordering deterministic when scores tie.
    return score, entry.get("id", "")


def main() -> int:
    entries = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    if not BACKUP_PATH.exists() and len(entries) > 80:
        shutil.copyfile(JSON_PATH, BACKUP_PATH)

    groups: dict[str, list[dict]] = defaultdict(list)
    for entry in entries:
        groups[style_key(entry)].append(entry)

    deduped: list[dict] = []
    for group_entries in groups.values():
        chosen = sorted(group_entries, key=representative_score, reverse=True)[0].copy()
        chosen["collapsed_count"] = sum(int(item.get("collapsed_count") or 1) for item in group_entries)
        product_urls = sorted({item.get("product_url", "") for item in group_entries if item.get("product_url")})
        chosen["product_url"] = product_urls[0] if product_urls else chosen.get("product_url", "")
        deduped.append(chosen)

    deduped.sort(key=lambda item: (item["category"], item["source"], item["title"], item["id"]))
    gallery.write_json(deduped)
    gallery.write_csv(deduped)
    gallery.write_html(deduped)
    print(f"Collapsed {len(entries)} image cards into {len(deduped)} style cards.")
    print(f"HTML: {gallery.HTML_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
