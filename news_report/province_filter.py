from pathlib import Path

import yaml

from news_report.models import Article

DEFAULT_PROVINCES_PATH = "config/provinces.yaml"

# These bare province names double as common Thai words/word-roots
# (แพร่ระบาด/แพร่หลาย/เผยแพร่ = "spread", ตากผ้า/ตากแดด = "dry/expose to sun"), so matching
# the bare name alone produces frequent false positives against ordinary Thai text.
# Only match these two provinces via their disambiguated forms (already present in
# provinces.yaml aliases: "จ.แพร่"/"จังหวัดแพร่"/"Phrae", "จ.ตาก"/"จังหวัดตาก"/"Tak").
_AMBIGUOUS_BARE_NAMES = {"แพร่", "ตาก"}


def load_provinces(config_path: str | Path = DEFAULT_PROVINCES_PATH) -> dict[str, list[str]]:
    """Returns {canonical_name: [match terms]}."""
    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    provinces: dict[str, list[str]] = {}
    for entry in data.get("provinces", []):
        name = entry["name"]
        aliases = entry.get("aliases", [])
        provinces[name] = aliases if name in _AMBIGUOUS_BARE_NAMES else [name, *aliases]
    return provinces


def match_provinces(text: str, provinces: dict[str, list[str]]) -> list[str]:
    """Substring match (case-insensitive) against each province's name/aliases."""
    haystack = text.lower()
    matched = [
        name
        for name, terms in provinces.items()
        if any(term.lower() in haystack for term in terms)
    ]
    return matched


def split_by_province(
    articles: list[Article],
    config_path: str | Path = DEFAULT_PROVINCES_PATH,
) -> tuple[list[Article], list[Article]]:
    """Splits articles into (matches >=1 target province, matches none), tagging matches.

    Kept deliberately broad/recall-favoring: an article matches if any target province's
    name is mentioned anywhere in the title/summary, even if the article isn't really
    "about" that province (e.g. it just quotes an official based there). The unmatched
    list isn't discarded so nothing gets silently dropped.
    """
    provinces = load_provinces(config_path)
    matched_articles: list[Article] = []
    unmatched_articles: list[Article] = []
    for article in articles:
        haystack = f"{article.title}\n{article.summary}"
        matched = match_provinces(haystack, provinces)
        if matched:
            article.provinces = matched
            matched_articles.append(article)
        else:
            unmatched_articles.append(article)
    return matched_articles, unmatched_articles


def filter_by_province(
    articles: list[Article],
    config_path: str | Path = DEFAULT_PROVINCES_PATH,
) -> list[Article]:
    """Keeps only articles mentioning at least one target province, tagging matches."""
    matched, _ = split_by_province(articles, config_path)
    return matched
