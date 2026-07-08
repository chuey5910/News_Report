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
    if not provinces:
        body = f"สรุปข่าว {report_date}\nไม่มีข่าวที่เกี่ยวข้องกับ 17 จังหวัดเป้าหมายวันนี้"
    else:
        total = sum(len(articles) for articles in provinces.values())
        lines = [f"สรุปข่าวประจำวันที่ {report_date} ({total} ข่าว)"]
        for province, articles in sorted(provinces.items()):
            lines.append(f"- {province}: {len(articles)} ข่าว")
        body = "\n".join(lines)

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
