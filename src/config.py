"""Application constants and hooks for later features.

Change HOMEPAGE or SEARCH_URL here rather than scattering strings in the UI.
"""

APP_NAME = "Web Surfer"
# Reverse-DNS id reserved for a future Gtk.Application / .desktop file.
APP_ID = "org.websurfer.WebSurfer"
DEFAULT_WIDTH = 1200
DEFAULT_HEIGHT = 800

# New tab and empty address bar. Rendered as local HTML (logo watermark).
HOMEPAGE = "websurfer:home"

# Non-URL queries are sent here. Later: a bundled SearxNG on 127.0.0.1.
SEARCH_URL = "https://duckduckgo.com/?q={query}"

# Passed to gi.require_version before importing Gtk / WebKit2.
WEBKIT_API = "4.1"
GTK_API = "3.0"

# Appearance. "system" follows the desktop GTK preference.
THEME_LIGHT = "light"
THEME_SYSTEM = "system"
THEME_DARK = "dark"
THEME_PSYCHEDELIC = "psychedelic"
THEME_MODES = (THEME_LIGHT, THEME_SYSTEM, THEME_DARK, THEME_PSYCHEDELIC)
DEFAULT_THEME = THEME_SYSTEM

# --- Future: Pi-hole / content filtering ---
# ENABLE_CONTENT_FILTERS = False
# FILTER_LIST_PATH = None
# PIHOLE_DNS = None

# --- Future: YouTube playback hooks ---
# ENABLE_YOUTUBE_HOOKS = False
