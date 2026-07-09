"""Flags "major" stories using a non-AI heuristic: articles whose titles are
near-duplicates of each other, published by enough distinct outlets in the same
run, are treated as widely-reported news.

Uses character n-gram (shingle) Jaccard similarity rather than word tokenization
so it works the same on Thai and English text without a word segmenter — every
title has already been translated to Thai by the time this runs anyway.

Limitation: clustering only runs within a single run's freshly-fetched batch,
not retroactively against articles already saved from an earlier run the same
day, so a story that breaks between runs won't merge across the 07:00/16:00
boundary.
"""

from news_report.models import Article

NGRAM_SIZE = 4
SIMILARITY_THRESHOLD = 0.35
MIN_SOURCES_FOR_MAJOR = 3


def _shingles(text: str, n: int = NGRAM_SIZE) -> set[str]:
    cleaned = "".join(text.lower().split())
    if len(cleaned) < n:
        return {cleaned} if cleaned else set()
    return {cleaned[i : i + n] for i in range(len(cleaned) - n + 1)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union else 0.0


class _UnionFind:
    def __init__(self, size: int):
        self._parent = list(range(size))

    def find(self, x: int) -> int:
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        root_a, root_b = self.find(a), self.find(b)
        if root_a != root_b:
            self._parent[root_a] = root_b


def tag_major_stories(
    articles: list[Article],
    ngram_size: int = NGRAM_SIZE,
    similarity_threshold: float = SIMILARITY_THRESHOLD,
    min_sources: int = MIN_SOURCES_FOR_MAJOR,
) -> None:
    """Mutates articles in place, setting is_major_story/major_story_source_count
    on every article in a title-cluster covered by >= min_sources distinct outlets."""
    if len(articles) < min_sources:
        return

    shingles = [_shingles(a.title, ngram_size) for a in articles]
    uf = _UnionFind(len(articles))
    for i in range(len(articles)):
        for j in range(i + 1, len(articles)):
            if _jaccard(shingles[i], shingles[j]) >= similarity_threshold:
                uf.union(i, j)

    clusters: dict[int, list[int]] = {}
    for i in range(len(articles)):
        clusters.setdefault(uf.find(i), []).append(i)

    for indices in clusters.values():
        source_count = len({articles[i].source for i in indices})
        if source_count >= min_sources:
            for i in indices:
                articles[i].is_major_story = True
                articles[i].major_story_source_count = source_count
