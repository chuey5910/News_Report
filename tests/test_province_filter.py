from news_report.models import Article
from news_report.province_filter import filter_by_province, match_provinces


def test_match_provinces_matches_alias_case_insensitive():
    provinces = {"เชียงใหม่": ["เชียงใหม่", "Chiang Mai"]}

    assert match_provinces("Flood hits Chiang Mai this week", provinces) == ["เชียงใหม่"]
    assert match_provinces("ไม่มีจังหวัดที่เกี่ยวข้อง", provinces) == []


def test_filter_by_province_tags_and_keeps_only_matches(tmp_path):
    config_path = tmp_path / "provinces.yaml"
    config_path.write_text(
        'provinces:\n  - name: เชียงใหม่\n    aliases: ["Chiang Mai"]\n',
        encoding="utf-8",
    )

    articles = [
        Article(guid="1", title="Chiang Mai flood", link="", summary="", published="", source="s", language="en"),
        Article(guid="2", title="Unrelated news", link="", summary="", published="", source="s", language="en"),
    ]

    result = filter_by_province(articles, config_path=config_path)

    assert len(result) == 1
    assert result[0].guid == "1"
    assert result[0].provinces == ["เชียงใหม่"]
