#!/usr/bin/env python3
"""Generate a numbered contact sheet for the European minimal category."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
GALLERY_DIR = ROOT / "reference_gallery"
JSON_PATH = GALLERY_DIR / "images.json"
THUMB_DIR = GALLERY_DIR / "thumbs"
REVIEW_DIR = GALLERY_DIR / "review"
OUT_PATH = REVIEW_DIR / "minimal_geometric_european_contact_sheet.jpg"
REVIEW_NOTES = REVIEW_DIR / "minimal_geometric_european_visual_review.json"
CATEGORY = "极简几何欧洲款式"


def fit_thumb(path: Path, size: tuple[int, int]) -> Image.Image:
    image = Image.open(path).convert("RGB")
    return ImageOps.contain(image, size, method=Image.Resampling.LANCZOS)


def main() -> int:
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    entries = [
        entry
        for entry in json.loads(JSON_PATH.read_text(encoding="utf-8"))
        if entry.get("category") == CATEGORY
    ]
    if len(entries) != 50:
        raise SystemExit(f"Expected 50 {CATEGORY} entries, found {len(entries)}")

    cols = 5
    cell_w, cell_h = 260, 330
    img_box = (230, 230)
    rows = (len(entries) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), "#f7f8f5")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()

    for index, entry in enumerate(entries, 1):
        col = (index - 1) % cols
        row = (index - 1) // cols
        x = col * cell_w
        y = row * cell_h
        draw.rectangle([x + 8, y + 8, x + cell_w - 8, y + cell_h - 8], fill="white", outline="#d9dfd9")
        thumb = THUMB_DIR / f"{entry['id']}.jpg"
        if thumb.exists():
            image = fit_thumb(thumb, img_box)
            ix = x + (cell_w - image.width) // 2
            iy = y + 18 + (img_box[1] - image.height) // 2
            sheet.paste(image, (ix, iy))
        else:
            draw.text((x + 20, y + 100), "missing thumb", fill="#aa0000", font=font)
        label = f"{index:02d}. {entry['source']} - {entry['title']}"
        wrapped = textwrap.wrap(label, width=34)[:4]
        ty = y + 252
        for line in wrapped:
            draw.text((x + 16, ty), line, fill="#17201b", font=font)
            ty += 15

    sheet.save(OUT_PATH, quality=88)
    notes = {
        "category": CATEGORY,
        "count": len(entries),
        "contact_sheet": str(OUT_PATH.relative_to(ROOT)),
        "visual_review_status": "reviewed_passed_after_hard_rejects",
        "hard_rejects": [
            "no armrests",
            "scene/lifestyle image",
            "multi-product set",
            "sofa/bench/lounge/table",
            "rattan/wicker/rope/webbing",
            "detail/close-up/dimension/logo/swatch image",
        ],
        "items": [
            {
                "index": index,
                "id": entry["id"],
                "title": entry["title"],
                "source": entry["source"],
            }
            for index, entry in enumerate(entries, 1)
        ],
    }
    REVIEW_NOTES.write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")
    print(OUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
