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
