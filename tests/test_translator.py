from unittest.mock import MagicMock, patch

from news_report.models import Article
from news_report.translator import translate_articles


@patch("news_report.translator.time.sleep")
@patch("news_report.translator.GoogleTranslator")
def test_translate_articles_translates_non_thai_and_keeps_original(mock_google_translator, _mock_sleep):
    mock_instance = MagicMock()
    mock_instance.translate.side_effect = lambda text: f"[TH]{text}"
    mock_google_translator.return_value = mock_instance

    articles = [
        Article(
            guid="1", title="Hello", link="http://x", summary="World",
            published="", source="BBC", language="en",
        ),
        Article(
            guid="2", title="สวัสดี", link="http://y", summary="โลก",
            published="", source="Matichon", language="th",
        ),
    ]

    result = translate_articles(articles)

    assert result[0].title == "[TH]Hello"
    assert result[0].summary == "[TH]World"
    assert result[0].title_original == "Hello"
    assert result[0].summary_original == "World"

    assert result[1].title == "สวัสดี"
    assert result[1].title_original is None
