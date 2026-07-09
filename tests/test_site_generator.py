import json

from news_report.site_generator import generate_site


def test_generate_site_writes_data_files_and_app_shell(tmp_path):
    reports_dir = tmp_path / "reports"
    output_dir = tmp_path / "docs"
    reports_dir.mkdir()

    report = {
        "date": "2026-07-08",
        "provinces": {
            "เชียงใหม่": [
                {
                    "guid": "1",
                    "title": "น้ำท่วมเชียงใหม่",
                    "link": "http://x/1",
                    "summary": "s",
                    "published": "",
                    "source": "มติชนออนไลน์",
                    "language": "th",
                    "source_origin": "domestic",
                    "provinces": ["เชียงใหม่"],
                    "title_original": None,
                    "summary_original": None,
                }
            ]
        },
        "general": [
            {
                "guid": "2",
                "title": "ข่าวทั่วไปไม่เกี่ยวกับ 17 จังหวัด",
                "link": "http://x/2",
                "summary": "s",
                "published": "",
                "source": "ข่าวสด",
                "language": "th",
                "source_origin": "domestic",
                "provinces": [],
                "title_original": None,
                "summary_original": None,
            }
        ],
    }
    (reports_dir / "2026-07-08.json").write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")

    generate_site(reports_dir=reports_dir, output_dir=output_dir, templates_dir="templates")

    assert (output_dir / "index.html").exists()
    assert json.loads((output_dir / "data" / "index.json").read_text(encoding="utf-8")) == ["2026-07-08"]

    saved_report = json.loads((output_dir / "data" / "2026-07-08.json").read_text(encoding="utf-8"))
    assert saved_report["provinces"]["เชียงใหม่"][0]["title"] == "น้ำท่วมเชียงใหม่"
    assert saved_report["general"][0]["title"] == "ข่าวทั่วไปไม่เกี่ยวกับ 17 จังหวัด"

    app_html = (output_dir / "index.html").read_text(encoding="utf-8")
    assert "province-list" in app_html
    assert "filter-search" in app_html
    assert "filter-origin" in app_html
