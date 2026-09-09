"""JSON bookmark store.

Schema (bookmarks.json under the user data dir)
    bar_visible: bool
    bar_order: ["folder:<id>", "item:<url>", ...]
    folders: [{id, name, on_bar, items: [{url, title, on_bar}]}]

"Show on bookmarks bar" is a flag on an item or folder. It is not a
special folder. A leftover folder id "bar" from earlier builds is
migrated into Other bookmarks with on_bar=True.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from gi.repository import GLib

OTHER_ID = "other"
BAR_ID = "bar"  # legacy only; migrated on load


def data_dir() -> Path:
    return Path(GLib.get_user_data_dir()) / "web-surfer"


def bookmarks_path() -> Path:
    return data_dir() / "bookmarks.json"


def _new_folder(folder_id: str, name: str, on_bar: bool = False) -> dict:
    return {"id": folder_id, "name": name, "on_bar": on_bar, "items": []}


class BookmarkStore:
    """Load, save, and mutate the on-disk bookmark tree."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else bookmarks_path()
        self.bar_visible = True
        self.folders: list[dict] = []
        self.bar_order: list[str] = []
        self.load()

    def load(self):
        self.bar_visible = True
        self.folders = [_new_folder(OTHER_ID, "Other bookmarks")]
        if not self.path.is_file():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if isinstance(raw, list):
            self.folder_by_id(OTHER_ID)["items"] = [
                self._normalize_item(i) for i in raw if isinstance(i, dict) and i.get("url")
            ]
            return
        if not isinstance(raw, dict):
            return
        self.bar_visible = bool(raw.get("bar_visible", True))
        incoming = raw.get("folders")
        if not isinstance(incoming, list):
            return
        cleaned = []
        bar_orphan_items = []
        for folder in incoming:
            if not isinstance(folder, dict):
                continue
            items = [
                self._normalize_item(i)
                for i in folder.get("items", [])
                if isinstance(i, dict) and i.get("url")
            ]
            folder_id = folder.get("id") or uuid.uuid4().hex[:8]
            if folder_id == BAR_ID:
                for item in items:
                    item["on_bar"] = True
                bar_orphan_items.extend(items)
                continue
            cleaned.append(
                {
                    "id": folder_id,
                    "name": folder.get("name") or "Folder",
                    "on_bar": bool(folder.get("on_bar", False)),
                    "items": items,
                }
            )
        if cleaned:
            self.folders = cleaned
        if self.folder_by_id(OTHER_ID) is None:
            self.folders.append(_new_folder(OTHER_ID, "Other bookmarks"))
        if bar_orphan_items:
            other = self.folder_by_id(OTHER_ID)
            other["items"].extend(bar_orphan_items)
        raw_order = raw.get("bar_order") if isinstance(raw, dict) else None
        self.bar_order = [x for x in raw_order if isinstance(x, str)] if isinstance(raw_order, list) else []
        self._sync_bar_order()

    def _normalize_item(self, item: dict) -> dict:
        return {
            "url": item.get("url"),
            "title": item.get("title") or item.get("url"),
            "on_bar": bool(item.get("on_bar", False)),
        }

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._sync_bar_order()
        payload = {
            "bar_visible": self.bar_visible,
            "folders": self.folders,
            "bar_order": self.bar_order,
        }
        self.path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def folder_by_id(self, folder_id: str) -> dict | None:
        for folder in self.folders:
            if folder.get("id") == folder_id:
                return folder
        return None

    def user_folders(self) -> list[dict]:
        return [f for f in self.folders if f.get("id") != OTHER_ID]

    def add_folder(self, name: str, on_bar: bool = False) -> dict:
        name = (name or "").strip() or "Folder"
        for folder in self.folders:
            if folder.get("name") == name:
                if on_bar:
                    folder["on_bar"] = True
                    self.save()
                return folder
        folder = _new_folder(uuid.uuid4().hex[:8], name, on_bar=on_bar)
        self.folders.append(folder)
        self.save()
        return folder

    def set_folder_on_bar(self, folder_id: str, on_bar: bool):
        folder = self.folder_by_id(folder_id)
        if folder is None or folder.get("id") == OTHER_ID:
            return
        folder["on_bar"] = bool(on_bar)
        self.save()

    def all_items(self) -> list[tuple[dict, dict]]:
        found = []
        for folder in self.folders:
            for item in folder.get("items", []):
                found.append((folder, item))
        return found

    def find(self, url: str) -> dict | None:
        pair = self.find_with_folder(url)
        return pair[1] if pair else None

    def find_with_folder(self, url: str) -> tuple[dict, dict] | None:
        url = (url or "").strip()
        for folder, item in self.all_items():
            if item.get("url") == url:
                return folder, item
        return None

    def add(
        self,
        url: str,
        title: str = "",
        folder_id: str = OTHER_ID,
        on_bar: bool | None = None,
        folder_on_bar: bool | None = None,
    ) -> dict:
        url = (url or "").strip()
        if not url:
            raise ValueError("empty url")
        dest = self.folder_by_id(folder_id) or self.folder_by_id(OTHER_ID)
        existing = self.find_with_folder(url)
        if existing:
            folder, item = existing
            if title:
                item["title"] = title
            if on_bar is not None:
                item["on_bar"] = bool(on_bar)
            if folder is not dest:
                self.move(url, dest["id"])
                item = self.find(url)
            if folder_on_bar is not None and dest.get("id") != OTHER_ID:
                dest["on_bar"] = bool(folder_on_bar)
            self.save()
            return item
        item = {
            "url": url,
            "title": title or url,
            "on_bar": bool(on_bar) if on_bar is not None else False,
        }
        dest["items"].append(item)
        if folder_on_bar is not None and dest.get("id") != OTHER_ID:
            dest["on_bar"] = bool(folder_on_bar)
        self.save()
        return item

    def move(self, url: str, folder_id: str) -> bool:
        pair = self.find_with_folder(url)
        dest = self.folder_by_id(folder_id)
        if not pair or dest is None:
            return False
        folder, item = pair
        if folder is dest:
            return True
        folder["items"] = [i for i in folder["items"] if i.get("url") != url]
        dest["items"].append(item)
        self.save()
        return True

    def remove(self, url: str) -> bool:
        url = (url or "").strip()
        changed = False
        for folder in self.folders:
            before = len(folder["items"])
            folder["items"] = [i for i in folder["items"] if i.get("url") != url]
            changed = changed or len(folder["items"]) != before
        if changed:
            self.save()
        return changed

    def bar_items(self) -> list[dict]:
        return [item for _folder, item in self.all_items() if item.get("on_bar")]

    def bar_folders(self) -> list[dict]:
        return [
            folder
            for folder in self.folders
            if folder.get("on_bar") and folder.get("id") != OTHER_ID
        ]

    def bar_key_folder(self, folder_id: str) -> str:
        return f"folder:{folder_id}"

    def bar_key_item(self, url: str) -> str:
        return f"item:{url}"

    def _sync_bar_order(self):
        wanted = []
        for folder in self.bar_folders():
            wanted.append(self.bar_key_folder(folder["id"]))
        for item in self.bar_items():
            wanted.append(self.bar_key_item(item["url"]))
        wanted_set = set(wanted)
        kept = [k for k in self.bar_order if k in wanted_set]
        for key in wanted:
            if key not in kept:
                kept.append(key)
        self.bar_order = kept

    def bar_entries(self) -> list[tuple[str, dict]]:
        self._sync_bar_order()
        entries = []
        for key in self.bar_order:
            kind, _, ident = key.partition(":")
            if kind == "folder":
                folder = self.folder_by_id(ident)
                if folder is not None and folder.get("on_bar"):
                    entries.append((key, "folder", folder))
            elif kind == "item":
                item = self.find(ident)
                if item is not None and item.get("on_bar"):
                    entries.append((key, "item", item))
        return entries

    def reorder_bar(self, src_key: str, dest_key: str, after: bool = False) -> bool:
        self._sync_bar_order()
        if src_key not in self.bar_order or dest_key not in self.bar_order:
            return False
        if src_key == dest_key and not after:
            return False
        order = list(self.bar_order)
        order.remove(src_key)
        idx = order.index(dest_key)
        if after:
            idx += 1
        order.insert(idx, src_key)
        if order == self.bar_order:
            return False
        self.bar_order = order
        self.save()
        return True

    def reorder_folders(self, src_id: str, dest_id: str, after: bool = False) -> bool:
        ids = [f["id"] for f in self.user_folders()]
        if src_id not in ids or dest_id not in ids:
            return False
        if src_id == dest_id and not after:
            return False
        ids.remove(src_id)
        idx = ids.index(dest_id)
        if after:
            idx += 1
        ids.insert(idx, src_id)
        lookup = {f["id"]: f for f in self.folders}
        others = [f for f in self.folders if f["id"] not in ids]
        self.folders = [lookup[i] for i in ids] + others
        self.save()
        return True

    def reorder_item(self, folder_id: str, src_url: str, dest_url: str, after: bool = False) -> bool:
        folder = self.folder_by_id(folder_id)
        if folder is None:
            return False
        urls = [i.get("url") for i in folder["items"]]
        if src_url not in urls or dest_url not in urls:
            return False
        if src_url == dest_url and not after:
            return False
        items = list(folder["items"])
        src = next(i for i in items if i.get("url") == src_url)
        items.remove(src)
        dest_idx = next(n for n, i in enumerate(items) if i.get("url") == dest_url)
        if after:
            dest_idx += 1
        items.insert(dest_idx, src)
        if items == folder["items"]:
            return False
        folder["items"] = items
        self.save()
        return True

    def toggle(self, url: str, title: str = "") -> bool:
        if self.find(url):
            self.remove(url)
            return False
        self.add(url, title)
        return True
