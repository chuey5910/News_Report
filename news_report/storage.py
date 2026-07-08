import json
import sqlite3
from contextlib import closing
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from news_report.models import Article

DEFAULT_DB_PATH = "data/seen.db"
DEFAULT_REPORTS_DIR = "data/reports"


def init_db(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_articles (
                guid TEXT PRIMARY KEY,
                first_seen_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def filter_unseen(articles: list[Article], db_path: str | Path = DEFAULT_DB_PATH) -> list[Article]:
    init_db(db_path)
    with closing(sqlite3.connect(db_path)) as conn:
        seen = {row[0] for row in conn.execute("SELECT guid FROM seen_articles")}
    return [a for a in articles if a.guid not in seen]


def mark_seen(articles: list[Article], db_path: str | Path = DEFAULT_DB_PATH) -> None:
    if not articles:
        return
    init_db(db_path)
    now = datetime.now(timezone.utc).isoformat()
    with closing(sqlite3.connect(db_path)) as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO seen_articles (guid, first_seen_at) VALUES (?, ?)",
            [(a.guid, now) for a in articles],
        )
        conn.commit()


def group_by_province(articles: list[Article]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for article in articles:
        for province in article.provinces:
            grouped.setdefault(province, []).append(asdict(article))
    return grouped


def save_daily_report(
    articles: list[Article],
    report_date: str,
    reports_dir: str | Path = DEFAULT_REPORTS_DIR,
) -> Path:
    """Groups articles by matched province and merges them into data/reports/<date>.json.

    Multiple runs on the same day (e.g. 07:00 and 16:00) accumulate into one
    report instead of overwriting each other, since `articles` only ever
    contains guids not previously marked seen.
    """
    Path(reports_dir).mkdir(parents=True, exist_ok=True)
    path = Path(reports_dir) / f"{report_date}.json"

    grouped: dict[str, list[dict]] = {}
    if path.exists():
        with open(path, encoding="utf-8") as f:
            grouped = json.load(f).get("provinces", {})

    for province, new_articles in group_by_province(articles).items():
        existing_guids = {a["guid"] for a in grouped.get(province, [])}
        grouped.setdefault(province, []).extend(
            a for a in new_articles if a["guid"] not in existing_guids
        )

    with open(path, "w", encoding="utf-8") as f:
        json.dump({"date": report_date, "provinces": grouped}, f, ensure_ascii=False, indent=2)
    return path
