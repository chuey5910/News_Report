from news_report.models import Article
from news_report.trending import tag_major_stories


def test_tag_major_stories_flags_story_covered_by_enough_sources():
    articles = [
        Article(guid="1", title="น้ำท่วมใหญ่ที่เชียงรายหลายอำเภอ", link="", summary="", published="", source="A", language="th"),
        Article(guid="2", title="น้ำท่วมใหญ่ที่เชียงรายหลายอำเภอ", link="", summary="", published="", source="B", language="th"),
        Article(guid="3", title="น้ำท่วมใหญ่ที่เชียงรายหลายอำเภอวันนี้", link="", summary="", published="", source="C", language="th"),
        Article(guid="4", title="ราคาน้ำมันปรับขึ้นทั่วประเทศวันนี้", link="", summary="", published="", source="D", language="th"),
    ]

    tag_major_stories(articles, min_sources=3)

    assert all(a.is_major_story for a in articles[:3])
    assert articles[0].major_story_source_count == 3
    assert not articles[3].is_major_story
    assert articles[3].major_story_source_count == 0


def test_tag_major_stories_ignores_cluster_with_too_few_distinct_sources():
    articles = [
        Article(guid="1", title="ข่าวเดียวกันเป๊ะทุกตัวอักษร", link="", summary="", published="", source="A", language="th"),
        Article(guid="2", title="ข่าวเดียวกันเป๊ะทุกตัวอักษร", link="", summary="", published="", source="B", language="th"),
    ]

    tag_major_stories(articles, min_sources=3)

    assert not any(a.is_major_story for a in articles)


def test_tag_major_stories_same_source_twice_does_not_count_as_two_sources():
    articles = [
        Article(guid="1", title="เรื่องเดียวกันซ้ำ", link="", summary="", published="", source="A", language="th"),
        Article(guid="2", title="เรื่องเดียวกันซ้ำ", link="", summary="", published="", source="A", language="th"),
        Article(guid="3", title="เรื่องเดียวกันซ้ำ", link="", summary="", published="", source="A", language="th"),
    ]

    tag_major_stories(articles, min_sources=3)

    assert not any(a.is_major_story for a in articles)  # only 1 distinct source
