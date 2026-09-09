"""Disk cache of site favicons as 16×16-friendly PNGs.

WebKit hands back a cairo surface that can be huge. Everything displayed
in tabs or menus is scaled down so the chrome stays compact.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from gi.repository import Gdk, GdkPixbuf

from .bookmarks import data_dir


def favicon_dir() -> Path:
    """~/.local/share/web-surfer/favicons/"""
    path = data_dir() / "favicons"
    path.mkdir(parents=True, exist_ok=True)
    return path


def favicon_path(url: str) -> Path:
    """Stable filename derived from the page URL."""
    digest = hashlib.sha256((url or "").encode("utf-8")).hexdigest()[:20]
    return favicon_dir() / f"{digest}.png"


def save_surface(url: str, surface) -> Path | None:
    """Persist a WebKit favicon surface as PNG. Returns the path or None."""
    if not url or surface is None:
        return None
    try:
        pixbuf = Gdk.pixbuf_get_from_surface(
            surface, 0, 0, surface.get_width(), surface.get_height()
        )
    except Exception:
        return None
    if pixbuf is None:
        return None
    dest = favicon_path(url)
    try:
        pixbuf.savev(str(dest), "png", [], [])
    except Exception:
        return None
    return dest


def scale_pixbuf(pixbuf: GdkPixbuf.Pixbuf | None, size: int = 16) -> GdkPixbuf.Pixbuf | None:
    """Force a square size (tab/menu icons are 16px)."""
    if pixbuf is None:
        return None
    if pixbuf.get_width() == size and pixbuf.get_height() == size:
        return pixbuf
    return pixbuf.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR)


def pixbuf_from_surface(surface, size: int = 16) -> GdkPixbuf.Pixbuf | None:
    """Cairo surface from WebView.get_favicon() → scaled pixbuf."""
    if surface is None:
        return None
    try:
        pixbuf = Gdk.pixbuf_get_from_surface(
            surface, 0, 0, surface.get_width(), surface.get_height()
        )
    except Exception:
        return None
    return scale_pixbuf(pixbuf, size)


def load_pixbuf(url: str, size: int = 16) -> GdkPixbuf.Pixbuf | None:
    """Read a cached PNG, scaled for display."""
    path = favicon_path(url)
    if not path.is_file():
        return None
    try:
        return GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path), size, size, True)
    except Exception:
        return None
