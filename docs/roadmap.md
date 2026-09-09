# Roadmap

## 0.1.1 — current

- Header bar: logo, compact tabs (favicon + title + close), new tab, − □ ×
- Start page `websurfer:home`: grayscale logo watermark at 30% opacity
- Tabs and related-view for `window.open`
- Bookmarks with folders, bar vs folder independence, drag reorder, flyouts
- Address bar select-all on first click

## Tabled

- Taskbar icon, `.desktop` export, AppImage — `docs/handoff-icons-packaging.md`

## 0.2 — search + settings

- Persist homepage and search endpoint
- Wire `SEARCH_URL` to a local or remote SearxNG instance

## 0.3 — content filters

- `WebKit2.UserContentFilterStore` with an EasyList-style filter
- Optional Pi-hole DNS / API check

## 0.4 — YouTube hooks

- Detect YouTube navigations in `decide-policy`
- Inject a small original user script
- Do not vendor SmartTube

## 0.5 — distribution

- Flatpak or AppImage
