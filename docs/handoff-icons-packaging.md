# Handoff: taskbar icon, .desktop launcher, AppImage

**Status:** tabled (2026-09-09). Do this after packaging is real.  
**Why tabled:** launching with `python3 web_surfer.py` inside Distrobox cannot give a stable Bazzite taskbar icon. An AppImage or exported `.desktop` is the right moment.

## Current facts

- App name: Web Surfer. Planned id: `org.websurfer.WebSurfer`.
- Stack: Python 3 + GTK 3 + WebKitGTK 4.1 (PyGObject). Not Chromium.
- License: GPL-3.0-or-later.
- Dev launch: Bazzite → Distrobox Fedora 42 → `python3 web_surfer.py`.
- Window chrome: `Gtk.HeaderBar` with minimize / maximize / close.
- Header logo works when the file is **`assets/logo.png`** (or `assets/logo.jpg`). Not `assets/icons/` unless we change the search list.
- Source art is a 960×960 cartoon surfer with a wide white margin. At 24–32px it turns into a pale square. Taskbar needs a tighter crop or a simplified badge.
- `self.set_icon(pixbuf)` does **not** reliably change the KDE/GNOME taskbar on Wayland.

## Why the taskbar is generic blue

The shell matches windows to a **`.desktop` file** + icon name + `StartupWMClass` / GTK application id. A raw `Gtk.Window` started as `python3` has none of those on the host.

Distrobox makes it worse: the process runs in the container. The host taskbar only sees a proper icon after `distrobox-export --app ...` or a host file in `~/.local/share/applications/`.

## Work to do later (order)

1. Crop or redraw a **square mark** for 16 / 32 / 48 / 128 / 256 PNG. Keep the full illustration for About / splash.
2. Install icons as `hicolor` theme names, e.g. `org.websurfer.WebSurfer.png`.
3. Switch the process from bare `Gtk.Window` + `Gtk.main()` to `Gtk.Application` with `application_id="org.websurfer.WebSurfer"`.
4. Add `web-surfer.desktop` (`Name`, `Exec`, `Icon`, `StartupWMClass`, `Categories=Network;WebBrowser;`).
5. On Bazzite, export that desktop file to the host (`distrobox-export` or copy to `~/.local/share/applications/` plus `~/.local/share/icons/hicolor/...`).
6. **AppImage (preferred packaging for “pin me”)**  
   - Tooling: python-appimage, Briefcase, or a custom squashfs that bundles Python + GI typelibs + WebKitGTK. WebKitGTK inside an AppImage is the hard part (GPU process, sandbox helpers, `libwebkit2gtk-4.1.so`).  
   - Alternative on Bazzite: Flatpak with WebKitGTK runtime. Often easier than AppImage for this stack.  
   - Do not `rpm-ostree` WebKit onto the host just for an icon.

## Out of scope until then

- Do not layer packages on Bazzite for branding.
- Do not treat the header logo as the taskbar fix.
- Donations / GitHub Sponsors are unrelated.

## Pointers in this repo

- `src/browser.py` — header bar + logo loader (`_LOGO_CANDIDATES`).
- `src/config.py` — `APP_NAME`, `APP_ID`.
- `assets/logo.png`, `assets/logo.jpg`.
- `docs/searxng.md` — search backend (separate track).
- `docs/roadmap.md` — packaging is listed as a later milestone.
