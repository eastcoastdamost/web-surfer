import json
from pathlib import Path

from src.bookmarks import OTHER_ID, BookmarkStore


def test_add_toggle(tmp_path: Path):
    store = BookmarkStore(tmp_path / "bookmarks.json")
    store.add("https://example.com", "Example")
    assert store.find("https://example.com")["title"] == "Example"
    assert store.toggle("https://example.com") is False
    assert store.find("https://example.com") is None
    assert store.toggle("https://example.com", "Example") is True
    data = json.loads((tmp_path / "bookmarks.json").read_text())
    urls = [i["url"] for f in data["folders"] for i in f["items"]]
    assert "https://example.com" in urls


def test_folder_and_bar_are_independent(tmp_path: Path):
    store = BookmarkStore(tmp_path / "bookmarks.json")
    news = store.add_folder("News")
    store.add("https://cnn.example", "CNN", folder_id=news["id"], on_bar=True)
    store.set_folder_on_bar(news["id"], True)
    assert store.find_with_folder("https://cnn.example")[0]["id"] == news["id"]
    assert store.find("https://cnn.example")["on_bar"] is True
    assert news["id"] in [f["id"] for f in store.bar_folders()]
    assert [i["url"] for i in store.bar_items()] == ["https://cnn.example"]


def test_migrates_legacy_bar_folder(tmp_path: Path):
    path = tmp_path / "bookmarks.json"
    path.write_text(
        json.dumps(
            {
                "bar_visible": True,
                "folders": [
                    {
                        "id": "bar",
                        "name": "Bookmarks bar",
                        "items": [{"url": "https://a.example", "title": "A"}],
                    },
                    {
                        "id": "other",
                        "name": "Other bookmarks",
                        "items": [{"url": "https://b.example", "title": "B"}],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    store = BookmarkStore(path)
    assert store.folder_by_id("bar") is None
    assert store.find("https://a.example")["on_bar"] is True
    assert store.find_with_folder("https://a.example")[0]["id"] == OTHER_ID


def test_migrates_legacy_list(tmp_path: Path):
    path = tmp_path / "bookmarks.json"
    path.write_text('[{"url": "https://old.example", "title": "Old"}]', encoding="utf-8")
    store = BookmarkStore(path)
    assert store.find("https://old.example")["title"] == "Old"
    assert store.find_with_folder("https://old.example")[0]["id"] == OTHER_ID
