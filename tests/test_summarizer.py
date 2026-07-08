from news_report.models import Article
from news_report.summarizer import format_reference, summarize_article


def test_summarize_article_strips_html_and_truncates():
    article = Article(
        guid="1",
        title="<b>Title</b>",
        link="http://x",
        summary="<p>" + "a" * 300 + "</p>",
        published="",
        source="s",
        language="th",
    )

    result = summarize_article(article, max_length=50)

    assert result.title == "Title"
    assert len(result.summary) == 50
    assert result.summary.endswith("…")


def test_format_reference_notes_translation():
    translated_article = Article(
        guid="1", title="t", link="http://x", summary="s",
        published="", source="BBC", language="en", title_original="Original",
    )
    ref = format_reference(translated_article)
    assert "แปลจากต้นฉบับ" in ref
    assert "http://x" in ref

    thai_article = Article(
        guid="2", title="t", link="http://y", summary="s",
        published="", source="Matichon", language="th",
    )
    ref = format_reference(thai_article)
    assert "แปลจากต้นฉบับ" not in ref
