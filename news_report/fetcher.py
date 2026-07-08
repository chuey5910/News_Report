import logging
from pathlib import Path

import feedparser
import yaml

from news_report.models import Article

logger = logging.getLogger(__name__)


def load_feeds(config_path: str | Path) -> list[dict]:
    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("feeds", [])


def fetch_feed(feed: dict) -> list[Article]:
    parsed = feedparser.parse(feed["url"])
    if parsed.bozo and not parsed.entries:
        raise ValueError(f"could not parse feed: {parsed.bozo_exception}")

    articles = []
    for entry in parsed.entries:
        link = entry.get("link", "")
        guid = entry.get("id") or link
        if not guid:
            continue
        articles.append(
            Article(
                guid=guid,
                title=(entry.get("title") or "").strip(),
                link=link,
                summary=entry.get("summary") or entry.get("description") or "",
                published=entry.get("published") or entry.get("updated") or "",
                source=feed["name"],
                language=feed.get("language", "th"),
                source_origin=feed.get("origin", "domestic"),
            )
        )
    return articles


def fetch_all(config_path: str | Path = "config/feeds.yaml") -> list[Article]:
    articles: list[Article] = []
    for feed in load_feeds(config_path):
        try:
            fetched = fetch_feed(feed)
            logger.info("fetched %d articles from %s", len(fetched), feed["name"])
            articles.extend(fetched)
        except Exception:
            logger.exception("failed to fetch feed %s (%s)", feed.get("name"), feed.get("url"))
    return articles
