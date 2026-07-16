import html
import re

_TAG_RE = re.compile(r"<[^>]+>")
_INLINE_WHITESPACE_RE = re.compile(r"[^\S\n]+")  # ทุก whitespace ยกเว้นขึ้นบรรทัดใหม่
_SPACE_AROUND_NEWLINE_RE = re.compile(r" ?\n ?")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")

# Many WordPress feeds (via plugins like WP RSS Aggregator / content-protection plugins)
# append a trailing "The post <title> first appeared on <site name>." notice to every
# single item's description. Left in place, that site name (e.g. "Chiang Rai Times")
# can spuriously match a target province's name/alias regardless of the article's
# actual topic. Strip it before translation/matching, not just before display.
_WP_SYNDICATION_FOOTER_RE = re.compile(
    r"(<p>)?(&lt;p&gt;)?\s*The post\b.*?\b(first appeared on|appeared first on)\b.*$",
    re.IGNORECASE | re.DOTALL,
)


def strip_syndication_footer(text: str) -> str:
    return _WP_SYNDICATION_FOOTER_RE.sub("", text).strip()


def strip_html(text: str) -> str:
    """Removes HTML tags and unescapes entities. Idempotent on already-clean text.

    Paragraph breaks (blank lines) are preserved — the web detail view renders
    them with `white-space: pre-wrap`, so multi-paragraph article bodies from
    the enricher stay readable instead of collapsing into one wall of text.
    """
    if not text:
        return ""
    without_tags = _TAG_RE.sub(" ", text)
    unescaped = html.unescape(without_tags)
    collapsed = _INLINE_WHITESPACE_RE.sub(" ", unescaped)
    collapsed = _SPACE_AROUND_NEWLINE_RE.sub("\n", collapsed)
    return _MULTI_NEWLINE_RE.sub("\n\n", collapsed).strip()


def truncate(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"
