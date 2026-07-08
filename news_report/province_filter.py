from pathlib import Path

import yaml

from news_report.models import Article

DEFAULT_PROVINCES_PATH = "config/provinces.yaml"


def load_provinces(config_path: str | Path = DEFAULT_PROVINCES_PATH) -> dict[str, list[str]]:
    """Returns {canonical_name: [canonical_name, *aliases]}."""
    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    provinces: dict[str, list[str]] = {}
    for entry in data.get("provinces", []):
        name = entry["name"]
        provinces[name] = [name, *entry.get("aliases", [])]
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


def filter_by_province(
    articles: list[Article],
    config_path: str | Path = DEFAULT_PROVINCES_PATH,
) -> list[Article]:
    """Keeps only articles mentioning at least one target province, tagging matches."""
    provinces = load_provinces(config_path)
    kept: list[Article] = []
    for article in articles:
        haystack = f"{article.title}\n{article.summary}"
        matched = match_provinces(haystack, provinces)
        if matched:
            article.provinces = matched
            kept.append(article)
    return kept
