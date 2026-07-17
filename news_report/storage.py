import json
import logging
import sqlite3
from contextlib import closing
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from news_report.models import Article

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "data/seen.db"
DEFAULT_REPORTS_DIR = "data/reports"
DEFAULT_BROADCAST_STATE_PATH = "data/last_broadcast.json"

# ข้อกำหนด: เก็บข่าวย้อนหลังได้ 7 วัน (รวมวันนี้) — เกินกว่านั้นลบทิ้ง
REPORT_RETENTION_DAYS = 7
# guid ใน seen.db ต้องอยู่นานกว่ารายงาน ไม่งั้นข่าวที่ยังค้างอยู่ใน RSS feed
# จะถูกนับเป็น "ข่าวใหม่" แล้วรายงานซ้ำหลังรายงานเก่าถูกลบ
SEEN_RETENTION_DAYS = 14


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


def was_round_broadcast(
    report_date: str,
    round_name: str,
    state_path: str | Path = DEFAULT_BROADCAST_STATE_PATH,
) -> bool:
    """True if a LINE broadcast already went out for this date+round (morning/afternoon).

    Guards against duplicate notifications when the workflow gets dispatched more than
    once for the same round (e.g. an upstream retry) — the file is committed together
    with the reports, so a queued second run sees the first run's broadcast.
    """
    path = Path(state_path)
    if not path.exists():
        return False
    try:
        with open(path, encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, ValueError):
        return False
    return state.get("date") == report_date and state.get("round") == round_name


def mark_round_broadcast(
    report_date: str,
    round_name: str,
    state_path: str | Path = DEFAULT_BROADCAST_STATE_PATH,
) -> None:
    path = Path(state_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"date": report_date, "round": round_name}, f, ensure_ascii=False)


def purge_old_data(
    today: str,
    reports_dir: str | Path = DEFAULT_REPORTS_DIR,
    db_path: str | Path = DEFAULT_DB_PATH,
    report_retention_days: int = REPORT_RETENTION_DAYS,
    seen_retention_days: int = SEEN_RETENTION_DAYS,
) -> list[str]:
    """Deletes daily reports older than the retention window (7 days incl. today)
    and prunes stale guids from seen.db. Returns the dates whose reports were removed.

    Files that don't look like a daily report (not named YYYY-MM-DD.json) are left alone.
    """
    today_date = date.fromisoformat(today)
    report_cutoff = today_date - timedelta(days=report_retention_days - 1)

    removed: list[str] = []
    reports_path = Path(reports_dir)
    if reports_path.is_dir():
        for path in sorted(reports_path.glob("*.json")):
            try:
                report_date = date.fromisoformat(path.stem)
            except ValueError:
                continue
            if report_date < report_cutoff:
                path.unlink()
                removed.append(path.stem)
    if removed:
        logger.info("purged %d report(s) older than %s: %s", len(removed), report_cutoff, removed)

    seen_cutoff = (
        datetime.now(timezone.utc) - timedelta(days=seen_retention_days)
    ).isoformat()
    init_db(db_path)
    with closing(sqlite3.connect(db_path)) as conn:
        cur = conn.execute("DELETE FROM seen_articles WHERE first_seen_at < ?", (seen_cutoff,))
        conn.commit()
        if cur.rowcount:
            logger.info("pruned %d stale guid(s) from seen.db", cur.rowcount)

    return removed


def group_by_province(articles: list[Article]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for article in articles:
        for province in article.provinces:
            grouped.setdefault(province, []).append(asdict(article))
    return grouped


def save_daily_report(
    articles: list[Article],
    general_articles: list[Article],
    report_date: str,
    reports_dir: str | Path = DEFAULT_REPORTS_DIR,
) -> Path:
    """Groups articles by matched province (plus a "general" bucket for everything that
    didn't match any of the 17 provinces) and merges them into data/reports/<date>.json.

    Multiple runs on the same day (e.g. 07:00 and 16:00) accumulate into one
    report instead of overwriting each other, since `articles`/`general_articles`
    only ever contain guids not previously marked seen.
    """
    Path(reports_dir).mkdir(parents=True, exist_ok=True)
    path = Path(reports_dir) / f"{report_date}.json"

    grouped: dict[str, list[dict]] = {}
    general: list[dict] = []
    if path.exists():
        with open(path, encoding="utf-8") as f:
            existing = json.load(f)
        grouped = existing.get("provinces", {})
        general = existing.get("general", [])

    for province, new_articles in group_by_province(articles).items():
        existing_guids = {a["guid"] for a in grouped.get(province, [])}
        grouped.setdefault(province, []).extend(
            a for a in new_articles if a["guid"] not in existing_guids
        )

    existing_general_guids = {a["guid"] for a in general}
    general.extend(
        asdict(a) for a in general_articles if a.guid not in existing_general_guids
    )

    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {"date": report_date, "provinces": grouped, "general": general},
            f,
            ensure_ascii=False,
            indent=2,
        )
    return path
