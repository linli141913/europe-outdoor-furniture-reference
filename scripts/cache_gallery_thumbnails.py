#!/usr/bin/env python3
"""Download and compress local thumbnails for the reference gallery."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
GALLERY_DIR = ROOT / "reference_gallery"
JSON_PATH = GALLERY_DIR / "images.json"
THUMB_DIR = GALLERY_DIR / "thumbs"
MANIFEST_PATH = THUMB_DIR / "manifest.json"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def preview_url(url: str) -> str:
    """Ask Shopify CDN for a smaller source before local compression."""
    parsed = urlparse(url)
    safe_path = quote(parsed.path, safe="/%:@")
    if "cdn.shopify.com" not in parsed.netloc.lower():
        return urlunparse((parsed.scheme, parsed.netloc, safe_path, "", parsed.query, ""))
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.setdefault("width", "900")
    return urlunparse((parsed.scheme, parsed.netloc, safe_path, "", urlencode(query), ""))


def download(url: str, destination: Path) -> None:
    req = Request(
        preview_url(url),
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Referer": "https://www.google.com/",
        },
    )
    with urlopen(req, timeout=20) as response:
        data = response.read(10 * 1024 * 1024)
    destination.write_bytes(data)


def make_thumb(source: Path, destination: Path) -> bool:
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "sips",
        "-Z",
        "620",
        "-s",
        "format",
        "jpeg",
        "-s",
        "formatOptions",
        "72",
        str(source),
        "--out",
        str(destination),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    return result.returncode == 0 and destination.exists() and destination.stat().st_size > 0


def cache_one(entry: dict) -> tuple[str, bool, str]:
    thumb_path = THUMB_DIR / f"{entry['id']}.jpg"
    marker = hashlib.sha1(entry["image_url"].encode("utf-8")).hexdigest()
    if thumb_path.exists() and thumb_path.stat().st_size > 0:
        return entry["id"], True, "cached"
    suffix = Path(urlparse(entry["image_url"]).path).suffix or ".img"
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = Path(tmp.name)
        try:
            download(entry["image_url"], tmp_path)
            ok = make_thumb(tmp_path, thumb_path)
            if ok:
                return entry["id"], True, marker
            return entry["id"], False, "convert failed"
        finally:
            tmp_path.unlink(missing_ok=True)
    except Exception as exc:
        return entry["id"], False, str(exc)


def main() -> int:
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    entries = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    total = len(entries)
    done = 0
    ok_count = 0
    failures: list[tuple[str, str]] = []
    start = time.time()

    workers = min(16, max(4, (os.cpu_count() or 4)))
    print(f"Creating local thumbnails for {total} images with {workers} workers...", flush=True)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(cache_one, entry) for entry in entries]
        for future in as_completed(futures):
            image_id, ok, detail = future.result()
            done += 1
            ok_count += 1 if ok else 0
            if not ok:
                failures.append((image_id, detail))
            if done % 25 == 0 or done == total:
                print(f"  {done}/{total} processed, {ok_count} local thumbs", flush=True)

    manifest = {
        "total": total,
        "local_thumbnails": ok_count,
        "failures": failures[:80],
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_seconds": round(time.time() - start, 1),
    }
    for entry in entries:
        thumb_path = THUMB_DIR / f"{entry['id']}.jpg"
        entry["thumb_url"] = f"thumbs/{entry['id']}.jpg" if thumb_path.exists() else ""
    JSON_PATH.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    gallery = importlib.import_module("build_real_reference_gallery")
    gallery.write_html(entries)
    gallery.write_csv(entries)
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Done: {ok_count}/{total} thumbnails cached in {THUMB_DIR}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
