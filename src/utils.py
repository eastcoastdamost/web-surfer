"""Turn address-bar text into either a URI or a search URL."""

from urllib.parse import quote_plus

from . import config


def looks_like_url(text: str) -> bool:
    """True when the text should load as a location, not a search query."""
    text = text.strip()
    if not text:
        return False
    lowered = text.lower()
    # Custom scheme websurfer: is the local start page.
    if lowered.startswith(("http://", "https://", "file://", "about:", "websurfer:")):
        return True
    if " " in text:
        return False
    # Bare hostnames: example.com or localhost
    if "." in text or lowered.startswith("localhost"):
        return True
    return False


def normalize_url(text: str) -> str:
    """Empty → homepage; URL-like → URI; otherwise SEARCH_URL with the query."""
    text = (text or "").strip()
    if not text:
        return config.HOMEPAGE
    if looks_like_url(text):
        if text.lower().startswith(
            ("http://", "https://", "file://", "about:", "websurfer:")
        ):
            return text
        return "https://" + text
    return config.SEARCH_URL.format(query=quote_plus(text))
