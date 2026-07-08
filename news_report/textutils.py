import html
import re

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")

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
    """Removes HTML tags and unescapes entities. Idempotent on already-clean text."""
    if not text:
        return ""
    without_tags = _TAG_RE.sub(" ", text)
    unescaped = html.unescape(without_tags)
    return _WHITESPACE_RE.sub(" ", unescaped).strip()


def truncate(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"
