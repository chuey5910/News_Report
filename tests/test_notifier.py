from news_report.notifier import build_broadcast_payload, build_summary_message


def test_build_summary_message_announces_without_per_province_breakdown():
    provinces = {"เชียงใหม่": [{"guid": "1"}], "เชียงราย": [{"guid": "2"}, {"guid": "3"}]}

    message = build_summary_message("2026-07-08", provinces, site_url="https://example.com/reports/2026-07-08.html")

    assert "3 ข่าว" in message
    assert "เชียงใหม่:" not in message  # no per-province breakdown anymore
    assert "https://example.com/reports/2026-07-08.html" in message


def test_build_summary_message_when_nothing_new():
    message = build_summary_message("2026-07-08", {})

    assert "ยังไม่มีข่าวใหม่" in message


def test_build_broadcast_payload_with_site_url_is_a_tappable_button():
    provinces = {"เชียงใหม่": [{"guid": "1"}]}

    payload = build_broadcast_payload("2026-07-08", provinces, site_url="https://example.com/?date=2026-07-08")

    assert payload["type"] == "template"
    assert payload["template"]["type"] == "buttons"
    action = payload["template"]["actions"][0]
    assert action["type"] == "uri"
    assert action["uri"] == "https://example.com/?date=2026-07-08"
    assert action["label"]


def test_build_broadcast_payload_without_site_url_falls_back_to_text():
    payload = build_broadcast_payload("2026-07-08", {"เชียงใหม่": [{"guid": "1"}]}, site_url=None)

    assert payload["type"] == "text"
    assert "เชียงใหม่:" not in payload["text"]  # plain announcement, no per-province breakdown
