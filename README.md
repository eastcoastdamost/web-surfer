# Web Surfer

A desktop browser built with **Python**, **GTK 3**, and **WebKitGTK** (PyGObject). It is not based on Chromium.

License: **GPL-3.0-or-later**. Donations only if you want; the code stays free.

## Requirements

On Fedora (including a Distrobox on Bazzite):

```bash
sudo dnf install -y python3 python3-gobject python3-cairo gtk3 webkit2gtk4.1
```

On Debian/Ubuntu:

```bash
sudo apt update
sudo apt install python3 python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1
```

WebKit API `4.1` is set in `src/config.py`. Change `WEBKIT_API` if your distro ships `4.0` or `6.0`.

## Run

From the repository root (inside Distrobox if you use Bazzite):

```bash
python3 web_surfer.py
python3 web_surfer.py https://example.com
```

If WebKit crashes on GPU/EGL inside a container:

```bash
WEBKIT_DISABLE_COMPOSITING_MODE=1 python3 web_surfer.py
```

## What works now

- Client-side header: logo, tabs, new-tab, window controls (− □ ×)
- New tab start page: grayscale Web Surfer logo at 30% opacity (`websurfer:home`)
- Address bar: first click selects all; double-click places the caret
- Typed text that is not a URL goes to DuckDuckGo (`SEARCH_URL` in `src/config.py`)
- Back / forward / reload follow the active tab
- Tabs: + or Ctrl+T, × or Ctrl+W, Ctrl+Tab to cycle, middle-click to close
- `window.open` / `target=_blank` open a related WebView tab (avoids a WebKit crash)
- Bookmarks stored in `~/.local/share/web-surfer/bookmarks.json`
  - Star dialog: name, folder, pin bookmark and/or folder to the bar
  - Bookmarks bar (~28px): drag with ghost + drop line, left/right insert
  - Bookmarks list (book icon): folders with hover flyouts, drag onto a folder to file
- Favicons cached under `~/.local/share/web-surfer/favicons/`
- Shared `WebKit2.WebContext` and `UserContentManager` for future filters

## Keyboard

| Shortcut | Action |
|---|---|
| Ctrl+T | New tab |
| Ctrl+W | Close tab |
| Ctrl+Tab / Ctrl+PageDown | Next tab |
| Ctrl+Shift+Tab / Ctrl+PageUp | Previous tab |
| Ctrl+L | Focus address bar |
| Ctrl+D | Bookmark / edit bookmark |
| Ctrl+B | Toggle bookmarks bar |

## Planned

1. In-browser content filters (Pi-hole-inspired EasyList via `UserContentFilterStore`)
2. YouTube playback hooks (original JS, not vendored SmartTube)
3. Bundled local SearxNG process — see `docs/searxng.md`
4. Packaging (Flatpak / AppImage) and a host `.desktop` icon — see `docs/handoff-icons-packaging.md`

## Layout

```
web-surfer/
├── src/
│   ├── main.py          # Gtk.main loop
│   ├── browser.py       # window, tabs, chrome, bookmarks UI
│   ├── bookmarks.py     # JSON store, folders, bar order
│   ├── favicons.py      # PNG cache for site icons
│   ├── config.py        # names, homepage, WebKit version
│   └── utils.py         # URL vs search
├── assets/              # logo.png / logo.jpg (header + start page)
├── tests/
├── docs/
├── web_surfer.py        # run from repo root
├── pyproject.toml
└── LICENSE
```

Logo files belong in `assets/`, not `assets/icons/`.

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[GNU General Public License v3.0 or later](LICENSE).
