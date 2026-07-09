from news_report.models import Article
from news_report.province_filter import (
    filter_by_province,
    load_provinces,
    match_provinces,
    split_by_province,
)


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


def test_ambiguous_province_names_require_disambiguated_form():
    provinces = load_provinces()

    # "แพร่ระบาด" (went viral/spread) is a common Thai phrase unrelated to Phrae province.
    assert match_provinces("ข่าวนี้แพร่ระบาดในโซเชียล", provinces) == []
    # But an explicit "จ.แพร่" / "Phrae" mention should still match.
    assert "แพร่" in match_provinces("น้ำท่วมที่ จ.แพร่ หนักมาก", provinces)
    assert "แพร่" in match_provinces("Flooding hit Phrae province", provinces)

    # "ตากผ้า" (hang laundry to dry) is unrelated to Tak province.
    assert match_provinces("แม่บ้านตากผ้าหน้าบ้าน", provinces) == []
    assert "ตาก" in match_provinces("จังหวัดตากเตือนภัยแล้ง", provinces)


def test_split_by_province_keeps_unmatched_articles_in_second_list(tmp_path):
    config_path = tmp_path / "provinces.yaml"
    config_path.write_text(
        'provinces:\n  - name: เชียงใหม่\n    aliases: ["Chiang Mai"]\n',
        encoding="utf-8",
    )

    articles = [
        Article(guid="1", title="Chiang Mai flood", link="", summary="", published="", source="s", language="en"),
        Article(guid="2", title="Unrelated news", link="", summary="", published="", source="s", language="en"),
    ]

    matched, unmatched = split_by_province(articles, config_path=config_path)

    assert [a.guid for a in matched] == ["1"]
    assert [a.guid for a in unmatched] == ["2"]
    assert unmatched[0].provinces == []  # nothing gets discarded, just untagged
