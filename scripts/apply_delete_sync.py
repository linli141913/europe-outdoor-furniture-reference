#!/usr/bin/env python3
"""Apply a browser-exported delete sync file to the local gallery."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib.parse import urlparse

import build_real_reference_gallery as gallery


ROOT = Path(__file__).resolve().parents[1]
GALLERY_DIR = ROOT / "reference_gallery"
JSON_PATH = GALLERY_DIR / "images.json"
DELETED_LOG = GALLERY_DIR / "deleted_items.json"
MANIFEST_PATH = GALLERY_DIR / "thumbs" / "manifest.json"


def latest_download() -> Path:
    downloads = Path.home() / "Downloads"
    candidates = sorted(
        downloads.glob("gallery-delete-sync-*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise SystemExit(f"No gallery-delete-sync-*.json file found in {downloads}")
    return candidates[0]


def read_ids(path: Path) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        ids = data
    elif isinstance(data, dict):
        ids = data.get("ids") or data.get("deleted_ids") or []
    else:
        ids = []
    output = {str(item).strip() for item in ids if str(item).strip()}
    if not output:
        raise SystemExit(f"No ids found in {path}")
    return output


def safe_delete_thumb(entry: dict) -> bool:
    thumb_url = entry.get("thumb_url") or ""
    if not thumb_url or thumb_url.startswith(("http://", "https://")):
        return False
    parsed = urlparse(thumb_url)
    thumb_path = (GALLERY_DIR / parsed.path).resolve()
    if GALLERY_DIR.resolve() not in thumb_path.parents:
        return False
    if not thumb_path.exists():
        return False
    thumb_path.unlink()
    return True


def update_manifest(entries: list[dict]) -> None:
    thumb_count = 0
    for entry in entries:
        thumb_url = entry.get("thumb_url") or ""
        if thumb_url and (GALLERY_DIR / thumb_url).exists():
            thumb_count += 1
    manifest = {
        "total": len(entries),
        "local_thumbnails": thumb_count,
        "failures": [],
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_seconds": 0.0,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply exported browser delete ids to reference_gallery.")
    parser.add_argument("delete_file", nargs="?", type=Path, help="Downloaded gallery-delete-sync JSON file.")
    parser.add_argument("--latest-download", action="store_true", help="Use the newest gallery-delete-sync JSON in ~/Downloads.")
    parser.add_argument("--dry-run", action="store_true", help="Report what would be deleted without changing files.")
    args = parser.parse_args()

    delete_file = latest_download() if args.latest_download else args.delete_file
    if not delete_file:
        parser.error("provide a delete_file or use --latest-download")
    ids = read_ids(delete_file)

    entries = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    removed = [entry for entry in entries if entry.get("id") in ids]
    kept = [entry for entry in entries if entry.get("id") not in ids]

    print(f"delete_file: {delete_file}")
    print(f"requested ids: {len(ids)}")
    print(f"matched gallery items: {len(removed)}")
    if not removed:
        return 0
    for entry in removed:
        print(f"- {entry.get('id')} | {entry.get('title')}")

    missing = sorted(ids - {entry.get("id") for entry in removed})
    if missing:
        print(f"ids not found: {len(missing)}")
        for item_id in missing[:40]:
            print(f"  ! {item_id}")

    if args.dry_run:
        return 0

    deleted_log = []
    if DELETED_LOG.exists():
        try:
            deleted_log = json.loads(DELETED_LOG.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            deleted_log = []
    sync_time = time.strftime("%Y-%m-%d %H:%M:%S")
    for entry in removed:
        entry = dict(entry)
        entry["deleted_at"] = sync_time
        entry["delete_sync_source"] = str(delete_file)
        deleted_log.append(entry)
    DELETED_LOG.write_text(json.dumps(deleted_log, ensure_ascii=False, indent=2), encoding="utf-8")

    deleted_thumbs = sum(1 for entry in removed if safe_delete_thumb(entry))

    favorites = gallery.read_favorites()
    favorites -= ids
    gallery.write_favorites(favorites)

    gallery.write_json(kept)
    gallery.write_csv(kept)
    gallery.write_html(kept)
    update_manifest(kept)

    print(f"deleted thumbnails: {deleted_thumbs}")
    print(f"remaining gallery items: {len(kept)}")
    print("Regenerated images.json, gallery.csv, index.html, favorites.html, and thumbnail manifest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
