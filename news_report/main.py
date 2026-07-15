import logging
import os
from datetime import datetime, timezone

from news_report import fetcher, notifier, site_generator, storage, summarizer, translator, trending
from news_report.province_filter import split_by_province

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

    logger.info("purging reports older than %d days", storage.REPORT_RETENTION_DAYS)
    storage.purge_old_data(report_date)

    logger.info("fetching articles from all feeds")
    articles = fetcher.fetch_all(FEEDS_CONFIG)

    logger.info("dropping previously seen articles (%d fetched)", len(articles))
    articles = storage.filter_unseen(articles)

    logger.info("translating non-Thai articles (%d unseen)", len(articles))
    articles = translator.translate_articles(articles)

    logger.info("filtering by target province")
    articles, general_articles = split_by_province(articles, PROVINCES_CONFIG)

    logger.info(
        "summarizing %d province-matched + %d general articles", len(articles), len(general_articles)
    )
    articles = summarizer.summarize_articles(articles)
    general_articles = summarizer.summarize_articles(general_articles)

    logger.info("tagging widely-reported (major) stories")
    trending.tag_major_stories(articles + general_articles)

    # Merged into that day's report (accumulates across same-day runs, e.g. 07:00 + 16:00)
    # rather than overwritten, since `articles`/`general_articles` here only ever hold
    # guids not seen before.
    new_by_province = storage.group_by_province(articles)
    report_path = storage.save_daily_report(articles, general_articles, report_date)
    logger.info("saved daily report to %s", report_path)

    # General articles are marked seen too, so they aren't re-fetched/re-translated
    # every run just to be discarded again — they're kept, not dropped.
    storage.mark_seen(articles + general_articles)

    site_generator.generate_site()
    logger.info("regenerated static site")

    if not new_by_province:
        logger.info("no new province-matched articles this run, skipping LINE broadcast")
        return

    site_base_url = os.environ.get("SITE_BASE_URL", "").rstrip("/")
    site_url = f"{site_base_url}/?date={report_date}" if site_base_url else None

    message = notifier.build_broadcast_payload(report_date, new_by_province, site_url)
    try:
        notifier.broadcast_message(message)
    except Exception:
        logger.exception("failed to send LINE broadcast (site + report were still generated)")


if __name__ == "__main__":
    run()
