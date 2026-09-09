# Roadmap

## 0.1 — current

Minimal window: URL bar, back, forward, reload, WebView.

## 0.2 — search + settings

- Persist homepage and search endpoint
- Wire `SEARCH_URL` to a local or remote SearxNG instance

## 0.3 — content filters

- `WebKit2.UserContentFilterStore` with a compiled EasyList-style filter
- Optional Pi-hole DNS / API check for blocked domains

## 0.4 — YouTube hooks

- Detect YouTube navigations in `decide-policy`
- Inject a small user script to skip or hide player ads
- Keep this original; do not vendor SmartTube

## 0.5 — distribution

- Flatpak manifest or AppImage
