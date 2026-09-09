from src.utils import looks_like_url, normalize_url


def test_looks_like_url():
    assert looks_like_url("https://example.com")
    assert looks_like_url("example.com")
    assert looks_like_url("localhost:8080")
    assert not looks_like_url("hello world")


def test_normalize_search():
    url = normalize_url("open source browsers")
    assert "q=open+source+browsers" in url or "q=open%20source%20browsers" in url


def test_normalize_bare_domain():
    assert normalize_url("example.com") == "https://example.com"
