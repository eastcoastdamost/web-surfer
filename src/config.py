"""Application constants and future-integration settings."""

APP_NAME = "Web Surfer"
APP_ID = "org.websurfer.WebSurfer"
DEFAULT_WIDTH = 1200
DEFAULT_HEIGHT = 800

# Homepage used when no URL is passed on the command line.
# SearxNG users can point this at their instance later.
HOMEPAGE = "https://duckduckgo.com"

# If a typed query does not look like a URL, treat it as a search.
# Later: a bundled local SearxNG, e.g.
#   SEARCH_URL = "http://127.0.0.1:8888/search?q={query}"
SEARCH_URL = "https://duckduckgo.com/?q={query}"

# WebKitGTK version to request via gi.require_version
WEBKIT_API = "4.1"
GTK_API = "3.0"

# --- Future: Pi-hole / content filtering ---
# ENABLE_CONTENT_FILTERS = False
# FILTER_LIST_PATH = None  # path to an EasyList-style filter or JSON rules
# PIHOLE_DNS = None        # e.g. "192.168.1.2"

# --- Future: YouTube playback hooks ---
# ENABLE_YOUTUBE_HOOKS = False
