from dataclasses import dataclass, field


@dataclass
class Article:
    """A single news item normalized across all RSS sources."""

    guid: str
    title: str
    link: str
    summary: str
    published: str
    source: str
    language: str
    source_origin: str = "domestic"
    provinces: list[str] = field(default_factory=list)
    title_original: str | None = None
    summary_original: str | None = None
