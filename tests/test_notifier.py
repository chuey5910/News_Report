from news_report.notifier import build_summary_message


def test_build_summary_message_announces_without_per_province_breakdown():
    provinces = {"เชียงใหม่": [{"guid": "1"}], "เชียงราย": [{"guid": "2"}, {"guid": "3"}]}

    message = build_summary_message("2026-07-08", provinces, site_url="https://example.com/reports/2026-07-08.html")

    assert "3 ข่าว" in message
    assert "เชียงใหม่:" not in message  # no per-province breakdown anymore
    assert "https://example.com/reports/2026-07-08.html" in message


def test_build_summary_message_when_nothing_new():
    message = build_summary_message("2026-07-08", {})

    assert "ยังไม่มีข่าวใหม่" in message
