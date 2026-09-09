# Web Surfer

A small desktop browser built with **Python**, **GTK 3**, and **WebKitGTK** (PyGObject). It is not based on Chromium.

Version 0.1 is intentionally minimal: a URL/search bar, back, forward, reload, and a WebKit view.

## Requirements

On Debian/Ubuntu:

```bash
sudo apt update
sudo apt install python3 python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1
```

WebKit API `4.1` is requested in `src/config.py`. If your distro only ships `4.0` or `6.0`, change `WEBKIT_API` there.

## Run

From the repository root:

```bash
python3 web_surfer.py
python3 web_surfer.py https://example.com
```

## What works now

- Back / forward / reload
- Address bar that accepts URLs or search terms
- Search terms go to DuckDuckGo (`SEARCH_URL` in `src/config.py`)
- Navigation buttons enable/disable with history
- A shared `WebKit2.WebContext` and `UserContentManager` ready for filters and scripts

## Planned features

1. **In-browser ad blocking (Pi-hole-inspired)**  
   Load content filters through `WebKit2.UserContentManager` / `UserContentFilterStore`, and optionally talk to a Pi-hole DNS or blocklists.

2. **YouTube playback hooks**  
   Use `decide-policy` plus `run_javascript()` or injected user scripts, drawing on ideas from SmartTube Beta — not embedding that project’s code.

3. **Built-in search via SearxNG**  
   SearxNG is a full web app (AGPL), not a library you `import`. The realistic
   “embedded” path is: Web Surfer starts a local SearxNG process on
   `127.0.0.1` and uses it as the search backend. See `docs/searxng.md`.

4. **Packaging**  
   `pyproject.toml` is in place. Flatpak or AppImage can come later.

## Repository layout

```
web-surfer/
├── src/
│   ├── main.py
│   ├── browser.py
│   ├── config.py
│   └── utils.py
├── assets/icons/
├── tests/
├── docs/
├── web_surfer.py
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[GNU General Public License v3.0 or later](LICENSE).

Web Surfer is free software: you can redistribute it and/or modify it under
the terms of the GNU GPL as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version.

Donations, if any, do not change the license. The program stays free.
