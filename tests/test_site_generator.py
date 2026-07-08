from news_report.site_generator import _build_render_report, _group_by_source


def test_group_by_source_orders_domestic_before_international():
    articles = [
        {"source": "BBC News - World", "source_origin": "international", "guid": "1"},
        {"source": "มติชนออนไลน์", "source_origin": "domestic", "guid": "2"},
        {"source": "Al Jazeera - All", "source_origin": "international", "guid": "3"},
        {"source": "ข่าวสด", "source_origin": "domestic", "guid": "4"},
    ]

    groups = _group_by_source(articles)

    assert [g["source"] for g in groups] == ["มติชนออนไลน์", "ข่าวสด", "BBC News - World", "Al Jazeera - All"]
    assert groups[0]["origin"] == "domestic"
    assert groups[-1]["origin"] == "international"


def test_build_render_report_computes_total_per_province():
    report = {
        "date": "2026-07-08",
        "provinces": {
            "เชียงใหม่": [
                {"source": "มติชนออนไลน์", "source_origin": "domestic", "guid": "1"},
                {"source": "BBC News - World", "source_origin": "international", "guid": "2"},
            ]
        },
    }

    rendered = _build_render_report(report)

    assert rendered["provinces"]["เชียงใหม่"]["total"] == 2
    assert [g["source"] for g in rendered["provinces"]["เชียงใหม่"]["sources"]] == ["มติชนออนไลน์", "BBC News - World"]
