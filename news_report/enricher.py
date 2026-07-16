"""ดึงเนื้อข่าวเต็มจากหน้าเว็บต้นทาง สำหรับข่าวที่ตรง 17 จังหวัดเป้าหมาย

RSS ส่วนใหญ่ให้แค่ description สั้นๆ 1-2 ประโยค อ่านแล้วไม่รู้รายละเอียด — โมดูลนี้
ตามลิงก์ไปหน้าข่าวจริง แล้วดึงย่อหน้าเนื้อความหลักออกมา (heuristic จาก <p> tags,
ไม่ใช้ AI) ทำเฉพาะข่าวที่ตรงจังหวัดเป้าหมาย (~10-20 ข่าว/รอบ) เพื่อไม่ให้ pipeline
ช้าเกินไป — ข่าวทั่วไปยังใช้ summary จาก RSS ตามเดิม
"""

import logging
import time
from html.parser import HTMLParser

import requests

from news_report import translator
from news_report.models import Article
from news_report.textutils import strip_html

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 12
INTER_REQUEST_DELAY_SECONDS = 0.3
# ย่อหน้าสั้นกว่านี้มักเป็น caption/เมนู/ปุ่ม ไม่ใช่เนื้อข่าว
MIN_PARAGRAPH_LENGTH = 60
# กันหน้า listing/รวมลิงก์: ต้องได้เนื้อความยาวกว่า summary เดิมพอสมควรถึงจะใช้แทน
MIN_GAIN_RATIO = 1.3
MAX_BODY_LENGTH = 3500
_SKIP_CONTAINERS = {"script", "style", "nav", "footer", "aside", "header", "form", "figure", "button"}
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36 NewsReportBot/1.0"
)


class _ParagraphExtractor(HTMLParser):
    """เก็บข้อความใน <p> ที่ไม่อยู่ใน script/nav/footer ฯลฯ"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.paragraphs: list[str] = []
        self._skip_depth = 0
        self._in_paragraph = False
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in _SKIP_CONTAINERS:
            self._skip_depth += 1
        elif tag == "p" and self._skip_depth == 0:
            self._in_paragraph = True
            self._buffer = []
        elif tag == "br" and self._in_paragraph:
            self._buffer.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_CONTAINERS:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag == "p" and self._in_paragraph:
            self._in_paragraph = False
            text = " ".join("".join(self._buffer).split())
            if len(text) >= MIN_PARAGRAPH_LENGTH:
                self.paragraphs.append(text)

    def handle_data(self, data: str) -> None:
        if self._in_paragraph and self._skip_depth == 0:
            self._buffer.append(data)


def extract_main_text(html: str, max_length: int = MAX_BODY_LENGTH) -> str:
    parser = _ParagraphExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception:  # HTML พังๆ จากบางเว็บ — ใช้เท่าที่ parse ได้
        pass

    body = "\n\n".join(parser.paragraphs)
    if len(body) <= max_length:
        return body
    # ตัดที่ขอบเขตย่อหน้า ไม่ตัดกลางประโยค
    truncated: list[str] = []
    used = 0
    for paragraph in parser.paragraphs:
        if used + len(paragraph) > max_length and truncated:
            break
        truncated.append(paragraph)
        used += len(paragraph) + 2
    return "\n\n".join(truncated)


def fetch_article_body(url: str) -> str:
    response = requests.get(
        url,
        headers={"User-Agent": _USER_AGENT, "Accept-Language": "th,en;q=0.8"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return extract_main_text(response.text)


def enrich_articles(articles: list[Article]) -> list[Article]:
    """เติมเนื้อข่าวเต็มให้ข่าวแต่ละชิ้น (in place) — ถ้าดึงไม่ได้/สั้นกว่าเดิม คง summary เดิมไว้

    ข่าวภาษาอื่นจะถูกแปลเนื้อความที่ได้เป็นไทย (summary เดิมถูกแปลมาก่อนแล้วในขั้น
    translate_articles ดังนั้นแปลเฉพาะเนื้อใหม่ที่เพิ่งดึงมา)
    """
    for article in articles:
        if not article.link:
            continue
        try:
            body = fetch_article_body(article.link)
        except Exception as exc:
            logger.warning("could not fetch full text for %s: %s", article.link, exc)
            continue

        current = strip_html(article.summary_original or article.summary)
        if len(body) < max(len(current), 1) * MIN_GAIN_RATIO:
            continue  # ได้ของสั้นกว่า/พอๆ กับของเดิม ไม่คุ้มเปลี่ยน

        if article.language != translator.TARGET_LANGUAGE:
            article.summary_original = body
            article.summary = translator.translate_text(body, article.language)
        else:
            article.summary = body
        time.sleep(INTER_REQUEST_DELAY_SECONDS)
    return articles
