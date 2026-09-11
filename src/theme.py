"""Persist and describe chrome appearance modes."""

from __future__ import annotations

import json
from pathlib import Path

from gi.repository import GLib

from . import config

VALID = set(config.THEME_MODES)


def data_dir() -> Path:
    return Path(GLib.get_user_data_dir()) / "web-surfer"


def settings_path() -> Path:
    return data_dir() / "settings.json"


def load_theme() -> str:
    path = settings_path()
    if not path.is_file():
        return config.DEFAULT_THEME
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return config.DEFAULT_THEME
    if not isinstance(raw, dict):
        return config.DEFAULT_THEME
    mode = str(raw.get("theme") or "").strip().lower()
    return mode if mode in VALID else config.DEFAULT_THEME


def save_theme(mode: str) -> None:
    mode = mode if mode in VALID else config.DEFAULT_THEME
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"theme": mode}
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                existing["theme"] = mode
                payload = existing
        except (OSError, json.JSONDecodeError):
            pass
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
