#!/usr/bin/env python3
"""Serve the local gallery and persist delete / favorite actions."""

from __future__ import annotations

import json
import sys
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import build_real_reference_gallery as gallery


ROOT = Path(__file__).resolve().parents[1]
GALLERY_DIR = ROOT / "reference_gallery"
JSON_PATH = GALLERY_DIR / "images.json"
DELETED_LOG = GALLERY_DIR / "deleted_items.json"


class GalleryHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(GALLERY_DIR), **kwargs)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path not in {"/api/delete", "/api/favorite"}:
            self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            item_id = str(payload.get("id") or "").strip()
            if not item_id:
                self._json_response({"ok": False, "error": "Missing id"}, HTTPStatus.BAD_REQUEST)
                return
            if path == "/api/delete":
                result = delete_item(item_id)
            else:
                result = set_favorite(item_id, bool(payload.get("favorite")))
            status = HTTPStatus.OK if result["ok"] else HTTPStatus.NOT_FOUND
            self._json_response(result, status)
        except Exception as exc:
            self._json_response({"ok": False, "error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def _json_response(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def delete_item(item_id: str) -> dict:
    entries = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    kept: list[dict] = []
    removed: dict | None = None
    for entry in entries:
        if entry.get("id") == item_id:
            removed = entry
        else:
            kept.append(entry)
    if not removed:
        return {"ok": False, "error": "Item not found"}

    deleted = []
    if DELETED_LOG.exists():
        try:
            deleted = json.loads(DELETED_LOG.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            deleted = []
    deleted.append(removed)
    DELETED_LOG.write_text(json.dumps(deleted, ensure_ascii=False, indent=2), encoding="utf-8")

    thumb_url = removed.get("thumb_url") or ""
    if thumb_url and not thumb_url.startswith(("http://", "https://")):
        thumb_path = (GALLERY_DIR / thumb_url).resolve()
        if GALLERY_DIR.resolve() in thumb_path.parents and thumb_path.exists():
            thumb_path.unlink()

    favorites = gallery.read_favorites()
    if item_id in favorites:
        favorites.discard(item_id)
        gallery.write_favorites(favorites)

    gallery.write_json(kept)
    gallery.write_csv(kept)
    gallery.write_html(kept)
    return {"ok": True, "deleted": removed.get("title"), "remaining": len(kept)}


def set_favorite(item_id: str, favorite: bool) -> dict:
    entries = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    existing_ids = {entry.get("id") for entry in entries}
    if item_id not in existing_ids:
        return {"ok": False, "error": "Item not found"}

    favorites = gallery.read_favorites()
    if favorite:
        favorites.add(item_id)
    else:
        favorites.discard(item_id)

    gallery.write_favorites(favorites)
    gallery.write_html(entries)
    return {
        "ok": True,
        "id": item_id,
        "favorite": item_id in favorites,
        "favorite_count": len(favorites),
    }


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    server = ThreadingHTTPServer(("127.0.0.1", port), GalleryHandler)
    print(f"Serving gallery with delete/favorite API at http://localhost:{port}/index.html", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
