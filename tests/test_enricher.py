from unittest.mock import patch

from news_report.enricher import enrich_articles, extract_main_text
from news_report.models import Article


SAMPLE_HTML = """
<html><head><title>x</title><script>var a = "ยาวมากๆ ไม่ควรติดมาในเนื้อข่าวเลยแม้แต่นิดเดียว";</script></head>
<body>
<nav><p>หน้าแรก การเมือง ภูมิภาค เศรษฐกิจ บันเทิง กีฬา ต่างประเทศ ไลฟ์สไตล์ อ่านข่าวทั้งหมดที่นี่</p></nav>
<article>
<p>เชียงใหม่ - เมื่อเวลา 10.00 น. วันนี้ เกิดเหตุน้ำป่าไหลหลากเข้าท่วมพื้นที่หมู่บ้านแม่ริมใต้ อ.แม่ริม จ.เชียงใหม่ หลังฝนตกหนักต่อเนื่องตลอดคืนที่ผ่านมา</p>
<p>สั้น</p>
<p>นายอำเภอแม่ริมเปิดเผยว่า ได้สั่งการให้เจ้าหน้าที่ อบต. และกู้ภัยเข้าช่วยเหลือประชาชนในพื้นที่แล้ว เบื้องต้นมีบ้านเรือนได้รับผลกระทบประมาณ 50 หลังคาเรือน ยังไม่มีรายงานผู้ได้รับบาดเจ็บ</p>
</article>
<footer><p>ติดตามข่าวสารได้ทาง Facebook Twitter Line TikTok YouTube ของเราได้ตลอด 24 ชั่วโมงทุกช่องทาง</p></footer>
</body></html>
"""


def test_extract_main_text_keeps_article_paragraphs_only():
    text = extract_main_text(SAMPLE_HTML)

    assert "น้ำป่าไหลหลาก" in text
    assert "นายอำเภอแม่ริม" in text
    # ย่อหน้าแยกกันด้วยบรรทัดว่าง
    assert "\n\n" in text
    # ของที่ไม่ใช่เนื้อข่าวต้องไม่ติดมา
    assert "หน้าแรก การเมือง" not in text  # nav
    assert "Facebook Twitter" not in text  # footer
    assert "var a" not in text  # script
    assert "สั้น" not in text  # ย่อหน้าสั้นเกินไป


def test_extract_main_text_truncates_at_paragraph_boundary():
    para = "ก" * 300
    html = "".join(f"<p>{para}</p>" for _ in range(30))

    text = extract_main_text(html, max_length=1000)

    assert len(text) <= 1000
    # ตัดที่ขอบย่อหน้า: ทุกย่อหน้าที่เหลือต้องยาวเต็ม 300 ตัวอักษร
    assert all(len(p) == 300 for p in text.split("\n\n"))


def _article(**overrides) -> Article:
    defaults = dict(
        guid="1", title="t", link="http://x/1", summary="สรุปสั้นจาก RSS",
        published="", source="s", language="th", provinces=["เชียงใหม่"],
    )
    defaults.update(overrides)
    return Article(**defaults)


@patch("news_report.enricher.fetch_article_body")
def test_enrich_replaces_summary_when_full_text_is_longer(mock_fetch):
    long_body = "เนื้อข่าวเต็มยาวมาก " * 30
    mock_fetch.return_value = long_body.strip()
    article = _article()

    enrich_articles([article])

    assert article.summary == long_body.strip()


@patch("news_report.enricher.fetch_article_body")
def test_enrich_keeps_summary_when_fetched_text_is_not_longer(mock_fetch):
    mock_fetch.return_value = "สั้นกว่าเดิม"
    article = _article(summary="สรุปเดิมจาก RSS ที่ยาวกว่าผลลัพธ์ที่ scrape มาได้")

    enrich_articles([article])

    assert article.summary == "สรุปเดิมจาก RSS ที่ยาวกว่าผลลัพธ์ที่ scrape มาได้"


@patch("news_report.enricher.fetch_article_body")
def test_enrich_keeps_summary_when_fetch_fails(mock_fetch):
    mock_fetch.side_effect = OSError("boom")
    article = _article()

    enrich_articles([article])

    assert article.summary == "สรุปสั้นจาก RSS"


@patch("news_report.enricher.translator.translate_text")
@patch("news_report.enricher.fetch_article_body")
def test_enrich_translates_foreign_articles(mock_fetch, mock_translate):
    body = "Full english article body " * 20
    mock_fetch.return_value = body.strip()
    mock_translate.return_value = "เนื้อข่าวแปลไทยแล้ว"
    article = _article(language="en", summary="สรุปแปลสั้นจากรอบ translate ก่อนหน้า")

    enrich_articles([article])

    assert article.summary == "เนื้อข่าวแปลไทยแล้ว"
    assert article.summary_original == body.strip()
    mock_translate.assert_called_once_with(body.strip(), "en")
