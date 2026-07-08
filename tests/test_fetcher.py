from unittest.mock import patch

from news_report.fetcher import fetch_feed


class _FakeParsed:
    def __init__(self, entries, bozo=False):
        self.entries = entries
        self.bozo = bozo
        self.bozo_exception = None


@patch("news_report.fetcher.feedparser.parse")
def test_fetch_feed_normalizes_entries(mock_parse):
    mock_parse.return_value = _FakeParsed(
        [
            {
                "title": " Test Title ",
                "link": "http://example.com/1",
                "summary": "Body",
                "published": "2026-01-01",
                "id": "guid-1",
            }
        ]
    )
    feed = {"name": "Test Source", "url": "http://example.com/rss", "language": "th"}

    articles = fetch_feed(feed)

    assert len(articles) == 1
    article = articles[0]
    assert article.title == "Test Title"
    assert article.guid == "guid-1"
    assert article.source == "Test Source"
    assert article.language == "th"


@patch("news_report.fetcher.feedparser.parse")
def test_fetch_feed_skips_entries_without_link_or_id(mock_parse):
    mock_parse.return_value = _FakeParsed([{"title": "No id", "summary": "x"}])
    feed = {"name": "Test Source", "url": "http://example.com/rss", "language": "th"}

    articles = fetch_feed(feed)

    assert articles == []
