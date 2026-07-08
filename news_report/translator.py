import logging
import time

from deep_translator import GoogleTranslator

from news_report.models import Article
from news_report.textutils import strip_html, truncate

logger = logging.getLogger(__name__)

TARGET_LANGUAGE = "th"
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2
INTER_REQUEST_DELAY_SECONDS = 0.5
# deep-translator's Google backend rejects requests over ~5000 chars.
MAX_INPUT_LENGTH = 4000


def translate_text(text: str, source_language: str, target_language: str = TARGET_LANGUAGE) -> str:
    cleaned = truncate(strip_html(text), MAX_INPUT_LENGTH)
    if not cleaned:
        return cleaned

    translator = GoogleTranslator(source=source_language, target=target_language)
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return translator.translate(cleaned)
        except Exception as exc:  # deep-translator raises various exceptions on rate-limit/network issues
            last_error = exc
            logger.warning("translate attempt %d/%d failed: %s", attempt, MAX_RETRIES, exc)
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    logger.error("translation failed after %d attempts, keeping original text: %s", MAX_RETRIES, last_error)
    return cleaned


def translate_articles(articles: list[Article], target_language: str = TARGET_LANGUAGE) -> list[Article]:
    """Translates non-Thai articles in place, preserving the original text for attribution."""
    for article in articles:
        if article.language == target_language:
            continue
        article.title_original = article.title
        article.summary_original = article.summary
        article.title = translate_text(article.title, article.language, target_language)
        article.summary = translate_text(article.summary, article.language, target_language)
        time.sleep(INTER_REQUEST_DELAY_SECONDS)
    return articles
