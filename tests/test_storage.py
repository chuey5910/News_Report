from news_report.models import Article
from news_report.storage import filter_unseen, mark_seen


def test_filter_unseen_and_mark_seen_roundtrip(tmp_path):
    db_path = tmp_path / "seen.db"
    article = Article(guid="1", title="t", link="http://x", summary="s", published="", source="s", language="th")

    assert filter_unseen([article], db_path=db_path) == [article]

    mark_seen([article], db_path=db_path)

    assert filter_unseen([article], db_path=db_path) == []
