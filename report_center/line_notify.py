"""แจ้งเตือนผ่าน LINE Official Account (Messaging API)

หลักการเดียวกับ sheets_sync:
- **ปิดโดยสมบูรณ์** ถ้าไม่ได้ตั้ง LINE_CHANNEL_ACCESS_TOKEN — ไม่มีข้อมูลออกนอกเครื่อง
- **ไม่มีทางทำให้การบันทึกล้มเหลว** — ทุก error ถูก log แล้วกลืน
- **ส่งเฉพาะข้อมูลขั้นต่ำ** (ชื่อกิจกรรม จังหวัด วันเวลา + ลิงก์เข้าระบบ)
  รายละเอียดลับทั้งหมดอยู่ในระบบ ต้องล็อกอิน + VPN ถึงจะเปิดลิงก์ได้

การส่ง: ถ้าตั้ง LINE_TARGET_IDS (userId/groupId คั่นด้วย ,) จะ push เข้าเป้าหมายนั้น
ถ้าไม่ตั้ง จะ broadcast ไปหาทุกคนที่เป็นเพื่อนกับ OA (เหมาะกับ OA ที่สร้างแยกเฉพาะทีม)
ใช้ urllib จาก stdlib — ไม่ต้องติดตั้งไลบรารีเพิ่มบนเครื่อง server
"""

import json
import logging
import os
import urllib.request

logger = logging.getLogger(__name__)

# override ได้ด้วย env LINE_API_BASE (ใช้ตอนทดสอบกับ endpoint ปลอม)
_API_BASE = os.environ.get("LINE_API_BASE", "https://api.line.me")
API_PUSH = f"{_API_BASE}/v2/bot/message/push"
API_BROADCAST = f"{_API_BASE}/v2/bot/message/broadcast"


def is_configured(config):
    return bool((config.get("LINE_CHANNEL_ACCESS_TOKEN") or "").strip())


def _post(url, token, payload):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return 200 <= resp.status < 300


def push_text(app, text):
    """ส่งข้อความเข้า LINE — คืน True เมื่อส่งสำเร็จ ไม่มีทาง raise."""
    config = app.config
    if not is_configured(config):
        logger.info("LINE notify skipped: LINE_CHANNEL_ACCESS_TOKEN not set")
        return False

    token = config["LINE_CHANNEL_ACCESS_TOKEN"].strip()
    targets = [t.strip() for t in (config.get("LINE_TARGET_IDS") or "").split(",") if t.strip()]
    message = {"type": "text", "text": text}
    try:
        if targets:
            return all(
                _post(API_PUSH, token, {"to": target, "messages": [message]}) for target in targets
            )
        return _post(API_BROADCAST, token, {"messages": [message]})
    except Exception as exc:  # ห้ามให้ปัญหา LINE กระทบการบันทึกข้อมูล
        logger.exception("LINE notify failed: %s", exc)
        return False


def _fmt_be(dt):
    return dt.strftime(f"%d/%m/{dt.year + 543} %H:%M") if dt else "-"


def _detail_link(config, report_id):
    base = (config.get("REPORT_CENTER_BASE_URL") or "").rstrip("/")
    return f"\nดูรายละเอียด: {base}/reports/{report_id}" if base else ""


def new_advance_message(config, item):
    """ข้อความแจ้งเตือนทันทีเมื่อมีการบันทึกข่าวล่วงหน้าใหม่."""
    return (
        "📢 ข่าวล่วงหน้าใหม่\n"
        f"กิจกรรม: {item.title}\n"
        f"สันติบาล จว.: {item.special_branch_province or '-'}\n"
        f"วันนัดหมาย: {_fmt_be(item.event_datetime)}"
        + _detail_link(config, item.id)
    )


def due_message(config, item, thai_now):
    """แจ้งเตือนใกล้ถึงกำหนดเวลาทำกิจกรรม (เรียกจากคำสั่ง `flask line-due` ผ่าน cron ทุก 5 นาที)."""
    minutes_left = round((item.event_datetime - thai_now).total_seconds() / 60)
    if minutes_left >= 1:
        header = f"⏰ อีกประมาณ {minutes_left} นาที ถึงกำหนดทำกิจกรรม"
    else:
        header = "⏰ ถึงกำหนดเวลาทำกิจกรรมแล้ว"
    return (
        f"{header}\n"
        f"กิจกรรม: {item.title}\n"
        f"สันติบาล จว.: {item.special_branch_province or '-'}\n"
        f"เวลานัดหมาย: {_fmt_be(item.event_datetime)}"
        + _detail_link(config, item.id)
    )


def daily_message(config, today_items, upcoming_items, today):
    """สรุปประจำเช้า: กิจกรรมวันนี้ + กิจกรรมล่วงหน้า 7 วันข้างหน้า (`flask line-daily`)
    เว้นบรรทัดว่างคั่นระหว่างแต่ละรายการ เพื่อให้อ่านในไลน์ได้ไม่สับสน"""
    # อีโมจิเน้นหน้ากิจกรรม: 🔴 วันนี้ / 🟠 ต่อเนื่องจากวันก่อน / 🔵 กำลังจะมาถึง
    today_lines = []
    for i, item in enumerate(today_items):
        if item.event_datetime < today:  # กิจกรรมหลายวันที่เริ่มก่อนหน้าและยังไม่จบ
            emoji, prefix = "🟠", "(ต่อเนื่อง) "
        else:
            time_part = item.event_datetime.strftime("%H:%M")
            emoji, prefix = "🔴", (f"{time_part} น. " if time_part != "00:00" else "")
        today_lines.append(f"{emoji} {i + 1}. {prefix}{item.title} — จว.{item.special_branch_province or '-'}")

    upcoming_lines = []
    for i, item in enumerate(upcoming_items):
        d = item.event_datetime
        time_part = d.strftime("%H:%M")
        time_str = f" {time_part} น." if time_part != "00:00" else ""
        upcoming_lines.append(
            f"🔵 {i + 1}. {d.day:02d}/{d.month:02d}{time_str} {item.title} — จว.{item.special_branch_province or '-'}"
        )

    item_gap = "\n\n"  # เว้น 1 บรรทัดระหว่างกิจกรรม
    today_block = (
        f"📌 กิจกรรมวันนี้ — {len(today_items)} รายการ\n\n" + item_gap.join(today_lines)
        if today_lines
        else "📌 กิจกรรมวันนี้ — ไม่มี"
    )
    upcoming_block = (
        f"📅 กิจกรรมล่วงหน้า 7 วันข้างหน้า — {len(upcoming_items)} รายการ\n\n" + item_gap.join(upcoming_lines)
        if upcoming_lines
        else "📅 กิจกรรมล่วงหน้า 7 วันข้างหน้า — ไม่มี"
    )

    message = (
        f"🗓 สรุปข่าวล่วงหน้า {today.day:02d}/{today.month:02d}/{today.year + 543}\n\n"
        + today_block
        + "\n\n\n"  # เว้น 2 บรรทัดคั่นระหว่าง 2 กลุ่ม
        + upcoming_block
    )
    base = (config.get("REPORT_CENTER_BASE_URL") or "").rstrip("/")
    if base:
        message += f"\n\nดูทั้งหมด: {base}/reports/"
    return message
