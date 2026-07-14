import json

from news_report.models import Article
from news_report.storage import filter_unseen, mark_seen, save_daily_report


def test_filter_unseen_and_mark_seen_roundtrip(tmp_path):
    db_path = tmp_path / "seen.db"
    article = Article(guid="1", title="t", link="http://x", summary="s", published="", source="s", language="th")

    assert filter_unseen([article], db_path=db_path) == [article]

    mark_seen([article], db_path=db_path)

    assert filter_unseen([article], db_path=db_path) == []


def test_save_daily_report_accumulates_across_same_day_runs(tmp_path):
    morning = Article(
        guid="1", title="เชียงใหม่เช้า", link="http://x/1", summary="s",
        published="", source="s", language="th", provinces=["เชียงใหม่"],
    )
    afternoon = Article(
        guid="2", title="เชียงใหม่บ่าย", link="http://x/2", summary="s",
        published="", source="s", language="th", provinces=["เชียงใหม่"],
    )

    save_daily_report([morning], [], "2026-07-08", reports_dir=tmp_path)
    path = save_daily_report([afternoon], [], "2026-07-08", reports_dir=tmp_path)

    report = json.loads(path.read_text(encoding="utf-8"))
    guids = {a["guid"] for a in report["provinces"]["เชียงใหม่"]}
    assert guids == {"1", "2"}


def test_save_daily_report_accumulates_general_bucket_across_runs(tmp_path):
    morning = Article(
        guid="10", title="ข่าวทั่วไปเช้า", link="http://x/10", summary="s",
        published="", source="s", language="th",
    )
    afternoon = Article(
        guid="11", title="ข่าวทั่วไปบ่าย", link="http://x/11", summary="s",
        published="", source="s", language="th",
    )

    save_daily_report([], [morning], "2026-07-08", reports_dir=tmp_path)
    path = save_daily_report([], [afternoon], "2026-07-08", reports_dir=tmp_path)

    report = json.loads(path.read_text(encoding="utf-8"))
    guids = {a["guid"] for a in report["general"]}
    assert guids == {"10", "11"}


def test_purge_old_data_removes_reports_older_than_7_days(tmp_path):
    from news_report.storage import purge_old_data

    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    for d in ["2026-07-07", "2026-07-08", "2026-07-14"]:
        (reports_dir / f"{d}.json").write_text("{}", encoding="utf-8")
    (reports_dir / "notes.json").write_text("{}", encoding="utf-8")

    removed = purge_old_data(
        "2026-07-14", reports_dir=reports_dir, db_path=tmp_path / "seen.db"
    )

    assert removed == ["2026-07-07"]
    assert not (reports_dir / "2026-07-07.json").exists()
    # 2026-07-08 คือวันเก่าสุดที่ยังอยู่ในช่วง 7 วัน (รวมวันนี้) — ต้องไม่ถูกลบ
    assert (reports_dir / "2026-07-08.json").exists()
    assert (reports_dir / "2026-07-14.json").exists()
    # ไฟล์ที่ไม่ใช่รายงานรายวัน ปล่อยไว้
    assert (reports_dir / "notes.json").exists()


def test_purge_old_data_prunes_stale_seen_guids(tmp_path):
    import sqlite3
    from news_report.storage import init_db, purge_old_data

    db_path = tmp_path / "seen.db"
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO seen_articles (guid, first_seen_at) VALUES (?, ?)",
            ("old", "2026-06-01T00:00:00+00:00"),
        )
        conn.execute(
            "INSERT INTO seen_articles (guid, first_seen_at) VALUES (?, ?)",
            ("recent", "2026-07-13T00:00:00+00:00"),
        )
        conn.commit()

    purge_old_data("2026-07-14", reports_dir=tmp_path / "none", db_path=db_path)

    with sqlite3.connect(db_path) as conn:
        remaining = {row[0] for row in conn.execute("SELECT guid FROM seen_articles")}
    assert remaining == {"recent"}
