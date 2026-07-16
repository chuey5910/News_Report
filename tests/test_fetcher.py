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


@patch("news_report.fetcher.feedparser.parse")
def test_fetch_feed_strips_wordpress_syndication_footer(mock_parse):
    mock_parse.return_value = _FakeParsed(
        [
            {
                "title": "Tornadoes hit central China",
                "link": "http://example.com/1",
                "summary": (
                    "<p>Severe storms tore through Hubei province on Monday. [&#8230;]</p>\n"
                    '<p>The post <a href="http://example.com/1">Tornadoes hit central China</a> '
                    'first appeared on <a href="https://www.chiangraitimes.com">Chiang Rai Times</a>.</p>'
                ),
                "id": "guid-1",
            }
        ]
    )
    feed = {"name": "Chiang Rai Times", "url": "http://example.com/rss", "language": "en"}

    articles = fetch_feed(feed)

    assert "Chiang Rai Times" not in articles[0].summary
    assert "Severe storms tore through Hubei province" in articles[0].summary


@patch("news_report.fetcher.feedparser.parse")
def test_fetch_feed_prefers_full_content_over_short_description(mock_parse):
    mock_parse.return_value = _FakeParsed(
        [
            {
                "title": "T",
                "link": "http://example.com/1",
                "id": "guid-1",
                "summary": "คำโปรยสั้น",
                "content": [{"value": "<p>เนื้อข่าวเต็มจาก content:encoded ที่ยาวกว่าคำโปรยมาก</p>"}],
            }
        ]
    )
    feed = {"name": "Test Source", "url": "http://example.com/rss", "language": "th"}

    articles = fetch_feed(feed)

    assert "เนื้อข่าวเต็มจาก content:encoded" in articles[0].summary
