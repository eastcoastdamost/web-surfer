"""Small helpers for navigation and input handling."""

from urllib.parse import quote_plus

from . import config


def looks_like_url(text: str) -> bool:
    """Return True if the typed text should be treated as a URL, not a search."""
    text = text.strip()
    if not text:
        return False
    lowered = text.lower()
    if lowered.startswith(("http://", "https://", "file://", "about:")):
        return True
    if " " in text:
        return False
    if "." in text or lowered.startswith("localhost"):
        return True
    return False


def normalize_url(text: str) -> str:
    """Turn a URL bar value into a loadable URI or a search URL."""
    text = (text or "").strip()
    if not text:
        return config.HOMEPAGE
    if looks_like_url(text):
        if text.lower().startswith(("http://", "https://", "file://", "about:")):
            return text
        return "https://" + text
    return config.SEARCH_URL.format(query=quote_plus(text))
