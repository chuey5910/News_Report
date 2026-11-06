"""การ์ดรายงาน (LINE Flex Message) — ส่งรายงาน 1 ฉบับเข้ากลุ่มไลน์เป็นการ์ดอ่านง่าย

หลักการ
- ใส่ข้อมูลครบทั้ง 15 ข้อ + ข้อมูลประกอบ (ประเภทกิจกรรม/กลุ่มปัญหา/การขออนุญาต)
- ข้อที่ยาวเกินจะตัด "ที่ท้ายประโยค" ไม่ตัดกลางคำ แล้วติดป้าย "ตัดบางส่วน"
  พร้อมปุ่มเปิดหน้ารายงานเต็ม (เห็นครบทุกข้อ)
- ส่งเมื่อผู้บันทึกติ๊กช่อง "ส่งการ์ดเข้ากลุ่มไลน์" เท่านั้น — ไม่ส่งเองอัตโนมัติ (ประหยัดโควตา)
- ล้มเหลวอย่างไรก็ไม่กระทบการบันทึกข้อมูล (ตัวส่งกลืน error ให้แล้ว)
"""

import hashlib
import hmac
from datetime import timedelta

from . import line_notify
from .models import (
    AFFILIATE_CATEGORIES,
    RELATED_ORG_CATEGORIES,
    REPORT_TYPE_LABELS,
    SITUATION_DEFAULT,
)

# หน่วยงานเจ้าของระบบ — ตรึงไว้เหมือนกันทุกการ์ด
UNIT_NAME = "กก.3.บก.ส.1"

THAI_MONTHS = [
    "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
]

CARD_TITLES = {
    "advance": "รายงานข่าวล่วงหน้า",
    "closure": "รายงานปิดข่าว",
    "incident": "รายงานเหตุการณ์/ข่าวทั่วไป",
}

# สีหัวการ์ดตามระดับสถานการณ์ (เหลือง/แดง สงวนไว้ 2 กรณีนี้เท่านั้น)
HEADER_COLORS = {"ปกติ": "#16305C", "เฝ้าระวัง": "#92590B", "มีผลกระทบ": "#8D1717"}
LEVEL_PILL = {
    "ปกติ": ("#16A34A", "#FFFFFF"),
    "เฝ้าระวัง": ("#EAB308", "#3B2C05"),
    "มีผลกระทบ": ("#DC2626", "#FFFFFF"),
}

LABEL_COLOR = "#1D4ED8"
TEXT_COLOR = "#1F2937"
MUTED_COLOR = "#6B7280"
LINE_COLOR = "#F1F2F4"
EMPTY = "ไม่ปรากฏ"

LONG_LIMIT = 220        # ตัวอักษรสูงสุดของข้อที่เป็นข้อความยาว
LIST_LIMIT = 6          # จำนวนบรรทัดสูงสุดของรายการ (แกนนำ/ยานพาหนะ/บุคคล)

ZWSP = "\u200b"         # ตัวแบ่งคำที่มองไม่เห็น — บอกไลน์ว่าตัดบรรทัดตรงนี้ได้


# ---------- ตัดคำภาษาไทย ----------

def _is_thai(ch):
    return "\u0e00" <= ch <= "\u0e7f"


def thai_words(text):
    """แยกข้อความเป็นคำ (ใช้ pythainlp ถ้ามี) — ไม่มีไลบรารีก็คืนทั้งก้อนเป็นคำเดียว."""
    try:
        from pythainlp.tokenize import word_tokenize
    except ImportError:  # ไม่มีไลบรารี = ไม่แทรกตัวแบ่งคำ ไลน์ยังแสดงผลได้ตามเดิม
        return [text]
    return word_tokenize(text, engine="newmm", keep_whitespace=True)


def thai_wrap(text):
    """แทรกตัวแบ่งคำที่มองไม่เห็นระหว่างคำไทย

    ภาษาไทยไม่มีช่องว่างระหว่างคำ ไลน์บางเครื่อง (เช่น LINE บน Mac) จึงตัดบรรทัดกลางคำ
    เช่น "เห|ตุการณ์" — ใส่ตัวแบ่งคำไว้ ไลน์จะเลือกตัดตรงรอยต่อคำแทน
    """
    if not text or not any(_is_thai(ch) for ch in text):
        return text
    out = []
    for line in text.split("\n"):
        words = thai_words(line)
        pieces = []
        for i, word in enumerate(words):
            if i and word and pieces and not word[0].isspace() and not pieces[-1][-1:].isspace() \
                    and pieces[-1][-1:] != "\u00a0" and (_is_thai(word[0]) or _is_thai(pieces[-1][-1:])):
                pieces.append(ZWSP)
            pieces.append(word)
        out.append("".join(pieces))
    return "\n".join(out)


# ---------- ตัวช่วยจัดข้อความ ----------

def shorten(text, limit=LONG_LIMIT):
    """ตัดข้อความยาวที่ท้ายประโยค/ท้ายคำ ไม่ตัดกลางคำ — คืน (ข้อความ, ถูกตัดไหม).

    ลำดับจุดตัด: ท้ายบรรทัด → ท้ายประโยค (ช่องว่างซึ่งภาษาไทยใช้คั่นประโยค) → ท้ายคำ
    """
    text = (text or "").strip()
    if len(text) <= limit:
        return text, False
    window = text[: limit + 1]
    cut = -1
    for sep in ("\n", " "):
        pos = window.rfind(sep)
        if pos >= limit * 0.5:   # ถ้าจุดตัดอยู่ต้นๆ เกินไป ข้อความจะสั้นผิดปกติ
            cut = pos
            break
    if cut < 0:
        # ไม่มีช่องว่างให้ตัด — ตัดที่รอยต่อคำสุดท้ายก่อนถึงขีดจำกัด
        pos = 0
        for word in thai_words(text):
            if pos + len(word) > limit:
                break
            pos += len(word)
        cut = pos if pos >= limit * 0.5 else limit
    return text[:cut].rstrip(" \n•·-\u00a0") + " …", True


def _bullets(lines):
    """รายการหลายบรรทัด — เกิน LIST_LIMIT จะสรุปว่าเหลืออีกกี่รายการ."""
    lines = [line for line in lines if line]
    if not lines:
        return EMPTY, False
    shown = lines[:LIST_LIMIT]
    text = "\n".join(f"• {line}" for line in shown)
    if len(lines) > LIST_LIMIT:
        return text + f"\n• และอีก {len(lines) - LIST_LIMIT} รายการ", True
    return text, False


def _keep_all(text, limit=None):
    """โหมดเต็ม — ไม่ตัดทอน (ใช้แทน shorten)."""
    return (text or "").strip(), False


def _bullets_all(lines):
    """โหมดเต็ม — แสดงทุกรายการ (ใช้แทน _bullets)."""
    lines = [line for line in lines if line]
    return ("\n".join(f"• {line}" for line in lines) if lines else EMPTY), False


def thai_datetime(dt, approx=False):
    if not dt:
        return None
    day = f"วันที่ {dt.day} {THAI_MONTHS[dt.month - 1]} {dt.year + 543}"
    if dt.hour == 0 and dt.minute == 0:
        return day
    prefix = "เวลาประมาณ" if approx else "เวลา"
    return f"{day} {prefix} {dt.hour:02d}.{dt.minute:02d} น."


def _split(value):
    return [v.strip() for v in (value or "").split(",") if v.strip()]


def tidy_bullets(text):
    """ขีดหน้าบรรทัด (- หรือ –) → • และผูกกับคำถัดไปด้วยช่องว่างแบบไม่ตัดบรรทัด

    ไลน์ตัดบรรทัดที่ช่องว่าง ข้อความไทยยาวๆ ไม่มีช่องว่างจึงถูกยกไปทั้งก้อน
    ทิ้งขีดไว้โดดๆ ท้ายบรรทัดบน (เห็นในการ์ดจริง) — ช่องว่างไม่ตัดบรรทัดแก้ตรงนี้
    """
    out = []
    for line in (text or "").splitlines():
        stripped = line.lstrip()
        if stripped[:1] in ("-", "–", "•") and stripped[1:2] in (" ", ""):
            stripped = "•\u00a0" + stripped[1:].lstrip()
        out.append(stripped)
    return "\n".join(out)


# ---------- เนื้อหา 15 ข้อ ----------

def card_rows(item, full=False):
    """(ไอคอน, เลขข้อ+หัวข้อ, ค่า, ถูกตัดไหม, ข้อมูลประกอบ, ลิงก์เพิ่ม) ของการ์ด 1 ใบ

    full=True = ไม่ตัดทอนอะไรเลย (ใช้กับหน้ารายงานเต็มและข้อความคัดลอก)
    """
    advance = item.report_type == "advance"
    rows = []

    cut_text = _keep_all if full else shorten
    bullets = _bullets_all if full else _bullets

    def add(icon, no, label, value, cut=False, extras=None, link=None, big=False):
        value = tidy_bullets(value)
        rows.append(
            {
                "icon": icon,
                "label": f"{no}. {label}",
                "value": value if (value or "").strip() else EMPTY,
                "empty": not (value or "").strip(),
                "cut": cut,
                "extras": extras or [],
                "link": link,
                "big": big,
            }
        )

    # 1 ชื่อกิจกรรม + ประเภทกิจกรรม/กลุ่มปัญหา
    kinds = []
    if _split(item.activity_types):
        kinds.append({"title": "ประเภทกิจกรรม", "chips": _split(item.activity_types), "tone": "activity"})
    if _split(item.problem_group_types):
        kinds.append({"title": "ประเภทกลุ่มปัญหา", "chips": _split(item.problem_group_types), "tone": "problem"})
    add("🎯", 1, "ชื่อกิจกรรม", item.title, extras=kinds, big=True)

    # 2 วันเวลา (มีวันสิ้นสุดก็ต่อท้าย)
    when = thai_datetime(item.event_datetime, approx=advance) or "-"
    end = thai_datetime(item.event_end_datetime)
    if end and item.event_end_datetime != item.event_datetime:
        when += f"\nถึง {end}"
    add("🗓", 2, "วันเวลาจัดกิจกรรม", when)

    # 3 สถานที่ + พิกัด + การขออนุญาต
    place = item.location or ""
    map_link = None
    if item.latitude is not None and item.longitude is not None:
        place += f"\n(พิกัด {item.latitude:.7f}, {item.longitude:.7f})"
        map_link = {
            "text": "🗺 เปิดแผนที่",
            "uri": f"https://www.google.com/maps/search/?api=1&query={item.latitude},{item.longitude}",
        }
    permit = []
    if item.permit_status:
        parts = [item.permit_status]
        if item.permit_location:
            parts.append(f"ที่ {item.permit_location}")
        if item.permit_duration_days:
            parts.append(f"ระยะเวลา {item.permit_duration_days} วัน")
        permit.append({"title": "การขออนุญาต", "text": " · ".join(parts)})
    add("📍", 3, "สถานที่จัดกิจกรรม", place, extras=permit, link=map_link)

    # 4 ชื่อกลุ่ม
    add("🏴", 4, "ชื่อกลุ่มที่จัดกิจกรรม", item.group_name)

    # 5 แกนนำ
    leader_lines = []
    for leader in item.leaders:
        line = leader.full_name
        if leader.position:
            line += f" ({leader.position})"
        leader_lines.append(line)
    text, cut = bullets(leader_lines)
    add("🗣", 5, "ชื่อแกนนำ", text, cut=cut)

    # 6 มวลชน
    mass_extras = []
    breakdown = [
        f"สมาชิกกลุ่ม: {item.mass_members}" if item.mass_members else None,
        f"นักข่าว/สื่อ: {item.mass_media}" if item.mass_media else None,
        f"อื่นๆ: {item.mass_others}" if item.mass_others else None,
    ]
    breakdown = [b for b in breakdown if b]
    if breakdown:
        mass_extras.append({"title": "จำแนกมวลชน", "text": "\n".join(breakdown)})
    mass_label = "คาดการณ์จำนวนมวลชนที่เข้าร่วม" if advance else "จำนวนมวลชน"
    add("👥", 6, mass_label, item.mass_count, extras=mass_extras)

    # 7 วัตถุประสงค์/ข้อเรียกร้อง
    text, cut = cut_text(item.demands)
    add("📣", 7, "วัตถุประสงค์และข้อเรียกร้อง", text, cut=cut)

    # 8 รูปแบบกิจกรรม (+ รายละเอียดการทำกิจกรรมของรายงานปิดข่าว/เหตุการณ์)
    text, cut = cut_text(item.activity_format)
    detail_extras = []
    if item.activity_detail:
        detail_text, detail_cut = cut_text(item.activity_detail)
        detail_extras.append({"title": "รายละเอียดการทำกิจกรรม", "text": detail_text})
        cut = cut or detail_cut
    add("🎪", 8, "รูปแบบ/ลักษณะการจัดกิจกรรม", text, cut=cut, extras=detail_extras)

    # 9 ยานพาหนะ
    if item.vehicle_status == "ไม่มี" or not item.vehicles:
        vehicle_text, vehicle_cut = (item.vehicle_status or ""), False
    else:
        lines = []
        for v in item.vehicles:
            parts = [p for p in (v.vehicle_type, v.plate_number and f"ทะเบียน {v.plate_number}",
                                 v.province, v.color and f"สี {v.color}") if p]
            lines.append(" ".join(parts))
        vehicle_text, vehicle_cut = bullets(lines)
    add("🚗", 9, "ยานพาหนะที่ใช้", vehicle_text, cut=vehicle_cut)

    # 10 สัมภาระค้างแรม/อุปกรณ์
    equipment = item.overnight_equipment_status or ""
    if item.overnight_equipment_detail:
        equipment += f" — {item.overnight_equipment_detail}"
    text, cut = cut_text(equipment)
    add("🎒", 10, "สัมภาระค้างแรม และอุปกรณ์ในการทำกิจกรรม", text, cut=cut)

    # 11 ผู้สนับสนุน (ข้อความอิสระ หรือรายชื่อที่กรอกเป็นช่องย่อย)
    support_lines = [
        p.full_name + (f" ({p.group_name})" if p.group_name else "")
        for p in item.people_of("supporter")
    ]
    if support_lines:
        text, cut = bullets(support_lines)
    else:
        text, cut = cut_text(item.supporters)
    add("💰", 11, "ผู้สนับสนุน/ผู้อยู่เบื้องหลัง", text, cut=cut)

    # 12 ความเกี่ยวข้อง/ความเชื่อมโยง + รายชื่อเครือข่าย/องค์กร
    linked = []
    for category in AFFILIATE_CATEGORIES:
        for p in item.people_of("affiliate", category):
            linked.append(f"{category}: {p.full_name}" + (f" ({p.group_name})" if p.group_name else ""))
    for category in RELATED_ORG_CATEGORIES:
        for p in item.people_of("related_org", category):
            linked.append(f"{category}: {p.full_name}" + (f" — {p.role}" if p.role else ""))
    base_text, cut = cut_text(item.affiliations)
    if linked:
        extra_text, extra_cut = bullets(linked)
        base_text = f"{base_text}\n{extra_text}" if base_text else extra_text
        cut = cut or extra_cut
    add("🔗", 12, "ความเกี่ยวข้อง/ความเชื่อมโยงกับการเมือง องค์กร หรือบุคคลอื่นๆ", base_text, cut=cut)

    # 13 ข้อมูลน่าสนใจอื่นๆ (+ สื่อออนไลน์ของรายงานปิดข่าว)
    text, cut = cut_text(item.other_info)
    media_extras = []
    if item.media_posts:
        lines = [
            f"{m.page_name} — Like {m.likes or '-'} / แชร์ {m.shares or '-'}" for m in item.media_posts
        ]
        media_text, media_cut = bullets(lines)
        media_extras.append({"title": "การเผยแพร่ทางสื่อออนไลน์", "text": media_text})
        cut = cut or media_cut
    add("🔍", 13, "ข้อมูลที่น่าสนใจอื่นๆ", text, cut=cut, extras=media_extras)

    # 14 ข้อพิจารณา
    text, cut = cut_text(item.considerations)
    add("⚖️", 14, "ข้อพิจารณา", text, cut=cut)

    # 15 แนวโน้ม
    text, cut = cut_text(item.trend_assessment)
    label = "แนวโน้มในอนาคต" if item.report_type == "closure" else "แนวโน้มสถานการณ์"
    add("📈", 15, label, text, cut=cut)

    return rows


# ---------- แปลงเป็น Flex JSON ----------

def _pill(text, bg, color):
    return {
        "type": "box",
        "layout": "vertical",
        "backgroundColor": bg,
        "cornerRadius": "12px",
        "paddingStart": "8px",
        "paddingEnd": "8px",
        "paddingTop": "2px",
        "paddingBottom": "2px",
        "flex": 0,
        "contents": [{"type": "text", "text": text, "size": "xs", "weight": "bold", "color": color}],
    }


def _chip(text, tone):
    bg, color = ("#E3EBFA", "#1E3A8A") if tone == "activity" else ("#EDE9FE", "#5B21B6")
    return {
        "type": "box",
        "layout": "vertical",
        "backgroundColor": bg,
        "cornerRadius": "10px",
        "paddingAll": "4px",
        "paddingStart": "9px",
        "paddingEnd": "9px",
        "margin": "xs",
        "contents": [{"type": "text", "text": thai_wrap(text), "size": "xs", "weight": "bold", "color": color, "wrap": True}],
    }


def _extra_block(extra):
    contents = [
        {"type": "text", "text": extra["title"], "size": "xs", "weight": "bold", "color": "#475569"}
    ]
    if extra.get("chips"):
        for chip in extra["chips"]:
            contents.append(_chip(chip, extra.get("tone", "activity")))
    if extra.get("text"):
        contents.append(
            {"type": "text", "text": thai_wrap(extra["text"]), "size": "sm", "color": "#334155", "wrap": True, "margin": "xs"}
        )
    return {
        "type": "box",
        "layout": "vertical",
        "backgroundColor": "#F6F8FC",
        "cornerRadius": "8px",
        "paddingAll": "9px",
        "margin": "sm",
        "contents": contents,
    }


def _row_block(row, detail_url):
    label_line = {
        "type": "box",
        "layout": "horizontal",
        "alignItems": "center",
        "contents": [
            {
                "type": "text",
                "text": thai_wrap(f"{row['icon']} {row['label']}"),
                "size": "sm",
                "weight": "bold",
                "color": LABEL_COLOR,
                "wrap": True,
                "flex": 1,
            }
        ],
    }
    if row["cut"]:
        label_line["contents"].append(_pill("ตัดบางส่วน", "#FEF3C7", "#92400E"))

    contents = [label_line, {
        "type": "text",
        "text": thai_wrap(row["value"]),
        "size": "lg" if row["big"] else "md",
        "weight": "bold" if row["big"] else "regular",
        "color": MUTED_COLOR if row["empty"] else TEXT_COLOR,
        "wrap": True,
        "margin": "xs",
    }]

    if row.get("link"):
        contents.append(
            {
                "type": "text",
                "text": row["link"]["text"],
                "size": "sm",
                "weight": "bold",
                "color": "#0E7490",
                "margin": "xs",
                "action": {"type": "uri", "label": "map", "uri": row["link"]["uri"]},
            }
        )
    for extra in row["extras"]:
        contents.append(_extra_block(extra))
    if row["cut"] and detail_url:
        number = row["label"].split(".")[0]
        contents.append(
            {
                "type": "text",
                "text": f"📄 อ่านข้อ {number} แบบเต็ม (เปิดรายงานเต็มทุกข้อ)",
                "size": "sm",
                "weight": "bold",
                "color": LABEL_COLOR,
                "margin": "xs",
                "action": {"type": "uri", "label": "full", "uri": detail_url},
            }
        )
    return {"type": "box", "layout": "vertical", "paddingTop": "8px", "paddingBottom": "8px", "contents": contents}


def tel_uri(phone):
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    return f"tel:{digits}" if len(digits) >= 9 else None


def share_token(config, report_id):
    """รหัสลับประจำรายงาน (คำนวณจาก SECRET_KEY) — ลิงก์ในการ์ดเปิดได้โดยไม่ต้องล็อกอิน
    แต่เดาเลขรายงานอื่นไม่ได้ และยังต้องอยู่บน Tailscale ถึงจะเปิดถึงเครื่องอยู่ดี"""
    key = (config.get("SECRET_KEY") or "").encode("utf-8")
    return hmac.new(key, f"share:{report_id}".encode("utf-8"), hashlib.sha256).hexdigest()[:24]


def share_url(config, report_id):
    base = (config.get("REPORT_CENTER_BASE_URL") or "").rstrip("/")
    return f"{base}/reports/{report_id}/s/{share_token(config, report_id)}" if base else None


def detail_url(config, report_id):
    """ลิงก์ที่ปุ่มในการ์ดใช้ = หน้ารายงานเต็มแบบไม่ต้องล็อกอิน."""
    return share_url(config, report_id)


def build_card(config, item):
    """สร้าง Flex bubble ของรายงาน 1 ฉบับ."""
    level = item.situation_level or SITUATION_DEFAULT
    header_color = HEADER_COLORS.get(level, HEADER_COLORS["ปกติ"])
    pill_bg, pill_color = LEVEL_PILL.get(level, LEVEL_PILL["ปกติ"])
    url = detail_url(config, item.id)
    title = CARD_TITLES.get(item.report_type, REPORT_TYPE_LABELS.get(item.report_type, "รายงานข่าว"))

    header_top = [
        {"type": "text", "text": f"📋 {title}", "color": "#FFFFFF", "weight": "bold", "size": "lg",
         "wrap": True, "flex": 1},
    ]
    if item.special_branch_province:
        header_top.append(_pill(f"ส.จว.{item.special_branch_province}", "#FBBF24", "#3B2C05"))

    sub = f"📌 {UNIT_NAME}"
    if item.ref_number:
        sub += f" · เลขที่ {item.ref_number}"
    header_sub = [
        {"type": "text", "text": sub, "size": "sm", "color": "#C7D7F0", "wrap": True, "flex": 1},
        _pill(level, pill_bg, pill_color),
    ]

    body = []
    for i, row in enumerate(card_rows(item)):
        if i:
            body.append({"type": "separator", "color": LINE_COLOR})
        body.append(_row_block(row, url))

    reporter = item.reporter_name or (item.created_by.full_name if item.created_by else "-")
    footer = []
    if item.photos:
        footer.append(
            {
                "type": "text",
                "text": f"📷 รูปแนบ {len(item.photos)} รูป — ดูได้ในรายงานเต็ม",
                "size": "sm",
                "weight": "bold",
                "color": "#0E7490",
                "wrap": True,
                "margin": "none",
            }
        )
    footer.append(
        {
            "type": "box",
            "layout": "baseline",
            "margin": "md" if item.photos else "none",
            "contents": [
                {"type": "text", "text": "👮 ผู้รายงาน", "size": "md", "color": MUTED_COLOR, "flex": 0},
                {"type": "text", "text": " ", "size": "md", "flex": 0},
                {"type": "text", "text": reporter, "size": "md", "weight": "bold", "color": TEXT_COLOR, "wrap": True},
            ],
        }
    )
    tel = tel_uri(item.reporter_phone)
    if tel:
        footer.append(
            {
                "type": "button",
                "style": "secondary",
                "height": "sm",
                "margin": "md",
                "action": {"type": "uri", "label": f"📞 โทร {reporter}"[:40], "uri": tel},
            }
        )
    if url:
        footer.append(
            {
                "type": "button",
                "style": "primary",
                "color": "#16305C",
                "height": "sm",
                "margin": "sm",
                "action": {"type": "uri", "label": "📨 ส่งต่อการ์ด / ดูรายงานเต็ม", "uri": url},
            }
        )

    bubble = {
        "type": "bubble",
        "size": "giga",   # กว้างที่สุดที่ไลน์อนุญาต (ไลน์เว้นที่รูปโปรไฟล์/เวลาไว้เสมอ เต็มจอ 100% ไม่ได้)
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": header_color,
            "paddingAll": "14px",
            "contents": [
                {"type": "box", "layout": "horizontal", "alignItems": "center", "contents": header_top},
                {
                    "type": "box",
                    "layout": "horizontal",
                    "alignItems": "center",
                    "margin": "sm",
                    "contents": header_sub,
                },
            ],
        },
        "body": {"type": "box", "layout": "vertical", "paddingAll": "14px", "contents": body},
        "footer": {"type": "box", "layout": "vertical", "paddingAll": "14px", "contents": footer},
    }
    _enable_scaling(bubble)
    return bubble


def _enable_scaling(node):
    """ให้ตัวอักษร/ปุ่มขยายตามขนาดตัวอักษรที่ผู้ใช้ตั้งไว้ในแอปไลน์ (เหมือนข้อความแชท)."""
    if isinstance(node, dict):
        if node.get("type") in ("text", "button"):
            node["scaling"] = True
        for value in node.values():
            _enable_scaling(value)
    elif isinstance(node, list):
        for value in node:
            _enable_scaling(value)


def alt_text(item):
    """ข้อความที่โผล่ในรายการแชท/แจ้งเตือนของไลน์ (การ์ดแสดงไม่ได้ในบางที่)."""
    title = CARD_TITLES.get(item.report_type, "รายงานข่าว")
    parts = [f"📋 {title}"]
    if item.special_branch_province:
        parts.append(f"ส.จว.{item.special_branch_province}")
    if item.ref_number:
        parts.append(f"เลขที่ {item.ref_number}")
    head = " · ".join(parts)
    when = thai_datetime(item.event_datetime, approx=item.report_type == "advance")
    return f"{head}\n{item.title}" + (f"\n{when}" if when else "")


def plain_text(config, item):
    """ข้อความสำหรับปุ่ม "คัดลอก" — หน้าตาเหมือนการ์ด (ไอคอน เลขข้อ เว้นบรรทัด) แต่ครบไม่ตัดทอน
    เอาไปวางเป็นข้อความธรรมดาในไลน์ได้เลย"""
    title = CARD_TITLES.get(item.report_type, "รายงานข่าว")
    level = item.situation_level or SITUATION_DEFAULT
    head = [f"📋 {title}" + (f" · ส.จว.{item.special_branch_province}" if item.special_branch_province else "")]
    meta = f"📌 {UNIT_NAME}"
    if item.ref_number:
        meta += f" · เลขที่ {item.ref_number}"
    meta += f" · ระดับ{level}"
    head.append(meta)

    blocks = ["\n".join(head)]
    for row in card_rows(item, full=True):
        lines = [f"{row['icon']} {row['label']}", row["value"].replace("\u00a0", " ")]
        for extra in row["extras"]:
            if extra.get("chips"):
                lines.append(f"  ▸ {extra['title']}: {', '.join(extra['chips'])}")
            elif extra.get("text"):
                lines.append(f"  ▸ {extra['title']}: {extra['text'].replace(chr(10), chr(10) + '    ')}")
        if row.get("link") and row["link"].get("uri", "").startswith("https://www.google.com/maps"):
            lines.append(f"  🗺 {row['link']['uri']}")
        blocks.append("\n".join(lines))

    reporter = item.reporter_name or (item.created_by.full_name if item.created_by else "-")
    foot = ""
    if item.photos:
        foot += f"📷 รูปแนบ {len(item.photos)} รูป (ดูในรายงานเต็ม)\n"
    foot += f"👮 ผู้รายงาน {reporter}"
    if item.reporter_phone:
        foot += f" · 📞 {item.reporter_phone}"
    thai_created = item.created_at + timedelta(hours=7)
    foot += f"\n🕓 บันทึกเมื่อ {thai_created.strftime(f'%d/%m/{thai_created.year + 543} %H:%M')} น."
    url = share_url(config, item.id)
    if url:
        foot += f"\n🔗 รายงานเต็ม: {url}"
    blocks.append(foot)
    return "\n\n".join(blocks)


def send_card(app, item):
    """ส่งการ์ดรายงานเข้ากลุ่มไลน์ — คืนสถานะของ line_notify (ไม่มีทาง raise)."""
    try:
        contents = build_card(app.config, item)
    except Exception as exc:  # ข้อมูลแปลกประหลาดต้องไม่ทำให้การบันทึกล้ม
        app.logger.error("สร้างการ์ดไลน์ไม่สำเร็จ: %s", exc)
        return line_notify.FAILED_PERMANENT
    return line_notify.push_flex_status(app, alt_text(item), contents)
