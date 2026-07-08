import logging
import os
from datetime import datetime, timezone

from news_report import fetcher, notifier, site_generator, storage, summarizer, translator
from news_report.province_filter import filter_by_province

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

FEEDS_CONFIG = "config/feeds.yaml"
PROVINCES_CONFIG = "config/provinces.yaml"
BANGKOK_UTC_OFFSET_HOURS = 7


def _today_bangkok() -> str:
    from datetime import timedelta

    return (datetime.now(timezone.utc) + timedelta(hours=BANGKOK_UTC_OFFSET_HOURS)).strftime("%Y-%m-%d")


def run(report_date: str | None = None) -> None:
    report_date = report_date or _today_bangkok()

    logger.info("fetching articles from all feeds")
    articles = fetcher.fetch_all(FEEDS_CONFIG)

    logger.info("dropping previously seen articles (%d fetched)", len(articles))
    articles = storage.filter_unseen(articles)

    logger.info("translating non-Thai articles (%d unseen)", len(articles))
    articles = translator.translate_articles(articles)

    logger.info("filtering by target province")
    articles = filter_by_province(articles, PROVINCES_CONFIG)

    logger.info("summarizing %d matched articles", len(articles))
    articles = summarizer.summarize_articles(articles)

    # Merged into that day's report (accumulates across same-day runs, e.g. 07:00 + 16:00)
    # rather than overwritten, since `articles` here only ever holds guids not seen before.
    new_by_province = storage.group_by_province(articles)
    report_path = storage.save_daily_report(articles, report_date)
    logger.info("saved daily report to %s", report_path)

    storage.mark_seen(articles)

    site_generator.generate_site()
    logger.info("regenerated static site")

    if not new_by_province:
        logger.info("no new province-matched articles this run, skipping LINE broadcast")
        return

    site_base_url = os.environ.get("SITE_BASE_URL", "").rstrip("/")
    site_url = f"{site_base_url}/reports/{report_date}.html" if site_base_url else None

    message = notifier.build_summary_message(report_date, new_by_province, site_url)
    try:
        notifier.broadcast_message(message)
    except Exception:
        logger.exception("failed to send LINE broadcast (site + report were still generated)")


if __name__ == "__main__":
    run()
