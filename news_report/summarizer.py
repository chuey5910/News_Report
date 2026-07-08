from news_report.models import Article
from news_report.textutils import strip_html, truncate

SUMMARY_MAX_LENGTH = 400


def summarize_article(article: Article, max_length: int = SUMMARY_MAX_LENGTH) -> Article:
    """Cleans HTML and truncates the summary. Idempotent if already cleaned by the translator."""
    article.title = strip_html(article.title)
    article.summary = truncate(strip_html(article.summary), max_length)
    return article


def summarize_articles(articles: list[Article], max_length: int = SUMMARY_MAX_LENGTH) -> list[Article]:
    return [summarize_article(article, max_length) for article in articles]


def format_reference(article: Article) -> str:
    """Attribution line for the original source, noting translation when applicable."""
    parts = [f"ที่มา: {article.source}"]
    if article.title_original is not None:
        parts.append("(แปลจากต้นฉบับ)")
    parts.append(article.link)
    return " ".join(parts)
