#!/usr/bin/env python3
"""Sync cloud-hidden gallery items into the local static gallery."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

import build_real_reference_gallery as gallery


ROOT = Path(__file__).resolve().parents[1]
GALLERY_DIR = ROOT / "reference_gallery"
JSON_PATH = GALLERY_DIR / "images.json"
DELETED_LOG = GALLERY_DIR / "deleted_items.json"
MANIFEST_PATH = GALLERY_DIR / "thumbs" / "manifest.json"
DEFAULT_SITE = "https://europe-outdoor-furniture-reference.vercel.app"


def read_cloud_hidden(site: str) -> dict:
    endpoint = urljoin(site.rstrip("/") + "/", "api/hidden")
    request = Request(endpoint, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise SystemExit(f"Failed to read {endpoint}: HTTP {exc.code} {detail}") from exc
    except URLError as exc:
        raise SystemExit(f"Failed to read {endpoint}: {exc.reason}") from exc

    if not payload.get("ok"):
        raise SystemExit(f"Cloud hidden API returned an error: {payload}")
    return payload


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


def apply_deletions(ids: set[str], records: list[dict], dry_run: bool) -> int:
    entries = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    record_by_id = {str(record.get("id")): record for record in records if record.get("id")}
    removed = [entry for entry in entries if entry.get("id") in ids]
    kept = [entry for entry in entries if entry.get("id") not in ids]
    missing = sorted(ids - {entry.get("id") for entry in removed})

    print(f"cloud hidden ids: {len(ids)}")
    print(f"matched local gallery items: {len(removed)}")
    for entry in removed:
        print(f"- {entry.get('id')} | {entry.get('title')}")

    if missing:
        print(f"ids already absent locally: {len(missing)}")
        for item_id in missing[:40]:
            print(f"  ! {item_id}")

    if dry_run:
        print("preview only; no local files changed.")
        return 0

    if not removed:
        print("nothing to apply.")
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
        entry["delete_sync_source"] = "cloud"
        if entry["id"] in record_by_id:
            entry["cloud_delete_record"] = record_by_id[entry["id"]]
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
    print("updated images.json, gallery.csv, index.html, favorites.html, app.js, favorites.json, and thumbnail manifest.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview or apply Vercel cloud deletion records locally.")
    parser.add_argument("--site", default=DEFAULT_SITE, help=f"Site origin to query. Default: {DEFAULT_SITE}")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--preview", action="store_true", help="Show cloud deletions that would be removed locally.")
    mode.add_argument("--apply", action="store_true", help="Remove cloud-hidden IDs from local gallery files.")
    args = parser.parse_args()

    payload = read_cloud_hidden(args.site)
    ids = {str(item).strip() for item in payload.get("ids", []) if str(item).strip()}
    records = payload.get("records") if isinstance(payload.get("records"), list) else []
    dry_run = not args.apply
    return apply_deletions(ids, records, dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
