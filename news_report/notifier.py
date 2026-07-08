import logging
import os

import requests

logger = logging.getLogger(__name__)

LINE_BROADCAST_URL = "https://api.line.me/v2/bot/message/broadcast"
MAX_LINE_MESSAGE_LENGTH = 5000  # LINE text message limit


def build_summary_message(
    report_date: str,
    provinces: dict[str, list[dict]],
    site_url: str | None = None,
) -> str:
    """A short announcement that a summary is ready — details live on the site, not in the message."""
    total = sum(len(articles) for articles in provinces.values())
    if total == 0:
        body = f"ยังไม่มีข่าวใหม่ที่เกี่ยวข้องกับ 17 จังหวัดเป้าหมาย ({report_date})"
    else:
        body = f"\U0001f4f0 สรุปข่าววันที่ {report_date} มีข่าวใหม่ {total} ข่าว อ่านได้แล้ววันนี้"

    if site_url:
        body += f"\n\nอ่านฉบับเต็ม: {site_url}"

    return body[:MAX_LINE_MESSAGE_LENGTH]


def broadcast_message(text: str, channel_access_token: str | None = None) -> None:
    token = channel_access_token or os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("LINE_CHANNEL_ACCESS_TOKEN is not set")

    response = requests.post(
        LINE_BROADCAST_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"messages": [{"type": "text", "text": text}]},
        timeout=15,
    )
    if response.status_code != 200:
        raise RuntimeError(f"LINE broadcast failed: {response.status_code} {response.text}")
    logger.info("LINE broadcast sent (%d chars)", len(text))
