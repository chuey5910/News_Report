from datetime import datetime, time as time_cls, timedelta

from flask import Blueprint, abort, current_app, render_template, redirect, request, url_for, flash
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from . import sheets_sync
from .admin import admin_required
from .extensions import db
from .forms import CLOSURE_TREND_PLACEHOLDER, NewsReportForm
from .models import (
    AFFILIATE_CATEGORIES,
    RELATED_ORG_CATEGORIES,
    REPORT_FORM_TABS,
    REPORT_TYPE_CHOICES,
    REPORT_TYPE_LABELS,
    SPECIAL_BRANCH_PROVINCES,
    NewsReport,
    NewsReportLeader,
    NewsReportMedia,
    NewsReportPerson,
    NewsReportVehicle,
)

bp = Blueprint("reports", __name__, url_prefix="/reports")

REPORT_FORM_TITLES = dict(REPORT_FORM_TABS)

# หมวดบุคคล/องค์กรแบบไดนามิก: (prefix ของชื่อ input, kind, category, ฟิลด์ย่อยที่มี)
# input จริงในฟอร์มชื่อ f"{prefix}_name" / f"{prefix}_group" / f"{prefix}_role"
PERSON_SECTIONS = [
    ("aff_net", "affiliate", AFFILIATE_CATEGORIES[0], ("name", "group")),
    ("aff_coord", "affiliate", AFFILIATE_CATEGORIES[1], ("name", "group")),
    ("aff_joint", "affiliate", AFFILIATE_CATEGORIES[2], ("name", "group")),
    ("participant", "participant", None, ("name", "group", "role")),
    ("supporter", "supporter", None, ("name", "group", "role")),
    ("org_party", "related_org", RELATED_ORG_CATEGORIES[0], ("name", "role")),
    ("org_ngo", "related_org", RELATED_ORG_CATEGORIES[1], ("name", "role")),
    ("org_gov", "related_org", RELATED_ORG_CATEGORIES[2], ("name", "role")),
]

# หมวดไหนโผล่ในแบบฟอร์มไหน
FORM_PERSON_PREFIXES = {
    "advance": ("aff_net", "aff_coord", "aff_joint"),
    "closure": ("participant", "supporter", "org_party", "org_ngo", "org_gov"),
    "incident": (),
}

PERSON_FIELD_LABELS = {
    "name": "ชื่อ-นามสกุล",
    "group": "กลุ่ม/ตำแหน่ง",
    "role": "บทบาท/หน้าที่",
}

THAI_WEEKDAYS = ["จันทร์", "อังคาร", "พุธ", "พฤหัสฯ", "ศุกร์", "เสาร์", "อาทิตย์"]
THAI_MONTHS_ABBR = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]

PERSON_SECTION_HEADINGS = {
    "aff_net": "เครือข่ายของกลุ่ม รายที่",
    "aff_coord": "ได้รับการประสานมาจาก รายที่",
    "aff_joint": "เคยร่วมกิจกรรมด้วยกับ รายที่",
    "participant": "แนวร่วม/บุคคลสำคัญ คนที่",
    "supporter": "ผู้สนับสนุน/ผู้อยู่เบื้องหลัง คนที่",
    "org_party": "พรรคการเมือง รายที่",
    "org_ngo": "NGO รายที่",
    "org_gov": "หน่วยงานรัฐ รายที่",
}


def _combine_date_time(date_val, time_val):
    if date_val is None:
        return None
    return datetime.combine(date_val, time_val or time_cls.min)


def _fields_from_form(form):
    permit_granted = form.permit_status.data == "มีการขออนุญาต"
    equipment_present = form.overnight_equipment_status.data == "มี"

    return {
        "special_branch_province": form.special_branch_province.data or None,
        "title": form.title.data,
        "activity_types": ", ".join(form.activity_types.data) or None,
        "problem_group_types": ", ".join(form.problem_group_types.data) or None,
        "event_datetime": _combine_date_time(form.event_date.data, form.event_time.data),
        "event_end_datetime": _combine_date_time(form.event_end_date.data, form.event_end_time.data),
        "permit_status": form.permit_status.data,
        "permit_location": form.permit_location.data if permit_granted else None,
        "permit_duration_days": form.permit_duration_days.data if permit_granted else None,
        "location": form.location.data,
        "group_name": form.group_name.data,
        "mass_count": form.mass_count.data,
        "mass_members": form.mass_members.data,
        "mass_media": form.mass_media.data,
        "mass_others": form.mass_others.data,
        "activity_format": form.activity_format.data,
        "demands": form.demands.data,
        "activity_detail": form.activity_detail.data,
        "supporters": form.supporters.data,
        "affiliations": form.affiliations.data,
        "overnight_equipment_status": form.overnight_equipment_status.data,
        "overnight_equipment_detail": form.overnight_equipment_detail.data if equipment_present else None,
        "vehicle_status": form.vehicle_status.data,
        "other_info": form.other_info.data,
        "trend_assessment": form.trend_assessment.data,
        "considerations": form.considerations.data,
        "reporter_name": form.reporter_name.data,
        "reporter_phone": form.reporter_phone.data,
    }


def _get_at(values, idx):
    return values[idx].strip() if idx < len(values) else ""


def _leaders_from_request():
    names = request.form.getlist("leader_name")
    positions = request.form.getlist("leader_position")
    roles = request.form.getlist("leader_role")
    leaders = []
    for i, name in enumerate(names):
        if name.strip():
            leaders.append(
                NewsReportLeader(
                    full_name=name.strip(),
                    position=_get_at(positions, i) or None,
                    role=_get_at(roles, i) or None,
                )
            )
    return leaders


def _vehicles_from_request():
    field_lists = {
        key: request.form.getlist(f"vehicle_{key}")
        for key in ("type", "plate", "province", "color", "owner", "usage")
    }
    count = max((len(v) for v in field_lists.values()), default=0)
    rows = []
    for i in range(count):
        values = {key: _get_at(lst, i) for key, lst in field_lists.items()}
        if any(values.values()):
            rows.append(
                NewsReportVehicle(
                    vehicle_type=values["type"] or None,
                    plate_number=values["plate"] or None,
                    province=values["province"] or None,
                    color=values["color"] or None,
                    owner=values["owner"] or None,
                    usage=values["usage"] or None,
                )
            )
    return rows


def _people_from_request(form_type):
    people = []
    for prefix, kind, category, _fields in PERSON_SECTIONS:
        if prefix not in FORM_PERSON_PREFIXES.get(form_type, ()):
            continue
        names = request.form.getlist(f"{prefix}_name")
        groups = request.form.getlist(f"{prefix}_group")
        roles = request.form.getlist(f"{prefix}_role")
        for i, name in enumerate(names):
            if name.strip():
                people.append(
                    NewsReportPerson(
                        kind=kind,
                        category=category,
                        full_name=name.strip(),
                        group_name=_get_at(groups, i) or None,
                        role=_get_at(roles, i) or None,
                    )
                )
    return people


def _media_from_request():
    pages = request.form.getlist("media_page")
    likes = request.form.getlist("media_likes")
    shares = request.form.getlist("media_shares")
    posts = []
    for i, page in enumerate(pages):
        if page.strip():
            posts.append(
                NewsReportMedia(
                    page_name=page.strip(),
                    likes=_get_at(likes, i) or None,
                    shares=_get_at(shares, i) or None,
                )
            )
    return posts


def _attach_children(item, form, form_type):
    """แทนที่รายการลูกทั้งหมด (แกนนำ/ยานพาหนะ/บุคคล/สื่อ) ด้วยค่าที่ส่งมาในฟอร์ม."""
    item.leaders = _leaders_from_request()
    item.vehicles = _vehicles_from_request() if form.vehicle_status.data == "มี" else []
    item.people = _people_from_request(form_type)
    item.media_posts = _media_from_request() if form_type == "closure" else []


# ---------- config สำหรับ activity-form.js (เรนเดอร์ช่องกรอกตามจำนวนที่เลือก) ----------

def _dynamic_sections(form_type, rows):
    """rows: dict key -> list[dict input_name -> value] ค่าเดิมไว้เติมกลับ (หน้าแก้ไข/ฟอร์มที่ validate ไม่ผ่าน)"""
    sections = []

    leader_fields = [{"name": "leader_name", "label": "ชื่อ-นามสกุล"}]
    if form_type == "closure":
        leader_fields += [
            {"name": "leader_position", "label": "ตำแหน่ง"},
            {"name": "leader_role", "label": "บทบาทหน้าที่"},
        ]
    sections.append(
        {
            "count": "leader_count",
            "container": "leader-fields-container",
            "heading": "แกนนำ คนที่",
            "fields": leader_fields,
            "rows": rows.get("leader", []),
        }
    )

    for prefix, _kind, _category, fields in PERSON_SECTIONS:
        if prefix not in FORM_PERSON_PREFIXES.get(form_type, ()):
            continue
        sections.append(
            {
                "count": f"{prefix}_count",
                "container": f"{prefix.replace('_', '-')}-fields-container",
                "heading": PERSON_SECTION_HEADINGS[prefix],
                "fields": [
                    {"name": f"{prefix}_{f}", "label": PERSON_FIELD_LABELS[f]} for f in fields
                ],
                "rows": rows.get(prefix, []),
            }
        )

    if form_type == "closure":
        sections.append(
            {
                "count": "media_count",
                "container": "media-fields-container",
                "heading": "สื่อออนไลน์ รายการที่",
                "fields": [
                    {"name": "media_page", "label": "ชื่อเพจ"},
                    {"name": "media_likes", "label": "ยอดคนกด Like"},
                    {"name": "media_shares", "label": "ยอดคนกดแชร์"},
                ],
                "rows": rows.get("media", []),
            }
        )

    vehicle_fields = [
        {"name": "vehicle_type", "label": "ประเภทรถยนต์"},
        {"name": "vehicle_plate", "label": "หมายเลขทะเบียน"},
        {"name": "vehicle_province", "label": "จังหวัด"},
        {"name": "vehicle_color", "label": "สี"},
    ]
    if form_type == "closure":
        vehicle_fields += [
            {"name": "vehicle_owner", "label": "เจ้าของ/ผู้ครอบครอง"},
            {"name": "vehicle_usage", "label": "ใช้ทำอะไรในกิจกรรม"},
        ]
    sections.append(
        {
            "count": "vehicle_count",
            "container": "vehicle-fields-container",
            "heading": "ยานพาหนะคันที่",
            "fields": vehicle_fields,
            "rows": rows.get("vehicle", []),
        }
    )

    return sections


def _form_config(form_type, rows):
    return {
        "toggles": [
            {"select": "permit_status", "value": "มีการขออนุญาต", "wrappers": ["permit-detail-wrapper"]},
            {"select": "overnight_equipment_status", "value": "มี", "wrappers": ["equipment-detail-wrapper"]},
            {
                "select": "vehicle_status",
                "value": "มี",
                "wrappers": ["vehicle-count-wrap", "vehicle-section-wrapper"],
            },
        ],
        "sections": _dynamic_sections(form_type, rows),
    }


def _rows_from_request():
    """เก็บค่าดิบที่ผู้ใช้กรอกไว้ เพื่อเรนเดอร์ฟอร์มกลับหลัง validate ไม่ผ่าน."""
    specs = {
        "leader": ["leader_name", "leader_position", "leader_role"],
        "vehicle": [
            "vehicle_type", "vehicle_plate", "vehicle_province",
            "vehicle_color", "vehicle_owner", "vehicle_usage",
        ],
        "media": ["media_page", "media_likes", "media_shares"],
    }
    for prefix, _kind, _category, fields in PERSON_SECTIONS:
        specs[prefix] = [f"{prefix}_{f}" for f in fields]

    rows = {}
    for key, names in specs.items():
        lists = [request.form.getlist(n) for n in names]
        count = max((len(lst) for lst in lists), default=0)
        rows[key] = [
            {names[j]: (lists[j][i] if i < len(lists[j]) else "") for j in range(len(names))}
            for i in range(count)
        ]
    return rows


def _rows_from_item(item):
    rows = {
        "leader": [
            {
                "leader_name": leader.full_name,
                "leader_position": leader.position or "",
                "leader_role": leader.role or "",
            }
            for leader in item.leaders
        ],
        "vehicle": [
            {
                "vehicle_type": v.vehicle_type or "",
                "vehicle_plate": v.plate_number or "",
                "vehicle_province": v.province or "",
                "vehicle_color": v.color or "",
                "vehicle_owner": v.owner or "",
                "vehicle_usage": v.usage or "",
            }
            for v in item.vehicles
        ],
        "media": [
            {"media_page": m.page_name, "media_likes": m.likes or "", "media_shares": m.shares or ""}
            for m in item.media_posts
        ],
    }
    for prefix, kind, category, _fields in PERSON_SECTIONS:
        rows[prefix] = [
            {
                f"{prefix}_name": p.full_name,
                f"{prefix}_group": p.group_name or "",
                f"{prefix}_role": p.role or "",
            }
            for p in item.people_of(kind, category)
        ]
    return rows


def _render_report_form(form, form_type, rows, edit_item=None):
    return render_template(
        "reports/report_form.html",
        form=form,
        form_type=form_type,
        form_title=REPORT_FORM_TITLES[form_type],
        form_config=_form_config(form_type, rows),
        trend_label="แนวโน้มในอนาคต" if form_type == "closure" else "แนวโน้มสถานการณ์",
        trend_placeholder=CLOSURE_TREND_PLACEHOLDER if form_type == "closure" else "",
        edit_item=edit_item,
    )


# ---------- หน้าเว็บ ----------

@bp.route("/")
@login_required
def dashboard():
    """ภาพรวม — ทุกคนที่ล็อกอินแล้วเข้าดูได้ ค้นหา/กรอง และดูผลวิเคราะห์รายจังหวัด."""
    q = (request.args.get("q") or "").strip()
    province = (request.args.get("province") or "").strip()
    rtype = (request.args.get("rtype") or "").strip()

    query = NewsReport.query
    if q:
        like = f"%{q}%"
        # ทะเบียนรถค้นแบบไม่สนช่องว่าง — พิมพ์ "กข1234" ต้องเจอ "กข 1234" ด้วย
        plate_like = f"%{q.replace(' ', '')}%"
        vehicle_match = NewsReport.vehicles.any(
            or_(
                NewsReportVehicle.vehicle_type.ilike(like),
                NewsReportVehicle.plate_number.ilike(like),
                func.replace(NewsReportVehicle.plate_number, " ", "").ilike(plate_like),
                NewsReportVehicle.province.ilike(like),
                NewsReportVehicle.owner.ilike(like),
            )
        )
        query = query.filter(
            or_(
                NewsReport.title.ilike(like),
                NewsReport.group_name.ilike(like),
                NewsReport.location.ilike(like),
                NewsReport.demands.ilike(like),
                NewsReport.other_info.ilike(like),
                NewsReport.reporter_name.ilike(like),
                NewsReport.leaders.any(NewsReportLeader.full_name.ilike(like)),
                NewsReport.people.any(NewsReportPerson.full_name.ilike(like)),
                vehicle_match,
            )
        )
    if province:
        query = query.filter(NewsReport.special_branch_province == province)
    if rtype in REPORT_TYPE_LABELS:
        query = query.filter(NewsReport.report_type == rtype)

    results = query.order_by(NewsReport.created_at.desc()).limit(200).all()

    # สรุปภาพรวมทั้งระบบ (ไม่ขึ้นกับตัวกรอง)
    counts = {"total": NewsReport.query.count()}
    for key, _label in REPORT_TYPE_CHOICES:
        counts[key] = NewsReport.query.filter_by(report_type=key).count()

    # วิเคราะห์แยกจังหวัด × ประเภทรายงาน (ตามตัวกรองที่เลือกอยู่ เพื่อให้ตารางสอดคล้องกับผลค้นหา)
    grouped = (
        query.with_entities(
            NewsReport.special_branch_province, NewsReport.report_type, func.count(NewsReport.id)
        )
        .group_by(NewsReport.special_branch_province, NewsReport.report_type)
        .all()
    )
    analysis = {}  # {province: {"advance": n, ..., "total": n}}
    for prov, type_key, n in grouped:
        prov = prov or "ไม่ระบุ"
        row = analysis.setdefault(prov, {key: 0 for key, _ in REPORT_TYPE_CHOICES})
        row[type_key] = row.get(type_key, 0) + n
    for row in analysis.values():
        row["total"] = sum(row.get(key, 0) for key, _ in REPORT_TYPE_CHOICES)
    # เรียงตามลำดับรายชื่อจังหวัดสันติบาล, "ไม่ระบุ" ไว้ท้ายสุด
    province_order = {name: i for i, name in enumerate(SPECIAL_BRANCH_PROVINCES)}
    analysis_rows = sorted(analysis.items(), key=lambda kv: province_order.get(kv[0], len(province_order)))

    # กิจกรรมที่กำลังจะมาถึง — ข่าวล่วงหน้าที่ถึงวันจริงภายใน 7 วันข้างหน้า (แจ้งเตือนเป็นปฏิทิน)
    # event_datetime ผู้ใช้กรอกเป็นเวลาไทยอยู่แล้ว จึงเทียบกับ "วันนี้" ตามเวลาไทย
    thai_now = datetime.utcnow() + timedelta(hours=7)
    today = thai_now.replace(hour=0, minute=0, second=0, microsecond=0)
    horizon = today + timedelta(days=8)  # วันนี้ + อีก 7 วัน
    upcoming = (
        NewsReport.query.filter(
            NewsReport.report_type == "advance",
            NewsReport.event_datetime >= today,
            NewsReport.event_datetime < horizon,
        )
        .order_by(NewsReport.event_datetime.asc())
        .all()
    )
    calendar_days = []
    for offset in range(8):
        day = today + timedelta(days=offset)
        calendar_days.append(
            {
                "weekday": THAI_WEEKDAYS[day.weekday()],
                "label": f"{day.day} {THAI_MONTHS_ABBR[day.month - 1]}",
                "is_today": offset == 0,
                "events": [r for r in upcoming if r.event_datetime.date() == day.date()],
            }
        )

    return render_template(
        "reports/dashboard.html",
        counts=counts,
        results=results,
        analysis_rows=analysis_rows,
        upcoming_count=len(upcoming),
        calendar_days=calendar_days,
        report_type_choices=REPORT_TYPE_CHOICES,
        provinces=SPECIAL_BRANCH_PROVINCES,
        q=q,
        province=province,
        rtype=rtype,
        filtered=bool(q or province or rtype),
    )


@bp.route("/new/<form_type>", methods=["GET", "POST"])
@login_required
def new_report(form_type):
    if form_type not in REPORT_FORM_TITLES:
        abort(404)

    form = NewsReportForm()
    if form.validate_on_submit():
        item = NewsReport(report_type=form_type, created_by_id=current_user.id, **_fields_from_form(form))
        _attach_children(item, form, form_type)
        db.session.add(item)
        db.session.commit()

        # Best-effort sync to Google Sheets (never blocks or fails the save)
        synced = sheets_sync.sync_report(current_app._get_current_object(), item)
        if sheets_sync.is_configured(current_app.config) and not synced:
            flash("บันทึกเรียบร้อย แต่ sync ขึ้น Google Sheets ไม่สำเร็จ (ดู log) — ข้อมูลถูกเก็บในระบบแล้ว", "warning")
        else:
            flash(f"บันทึก{REPORT_FORM_TITLES[form_type]}เรียบร้อยแล้ว", "success")
        return redirect(url_for("reports.new_report", form_type=form_type))

    rows = _rows_from_request() if request.method == "POST" else {}
    return _render_report_form(form, form_type, rows)


# เส้นทางเดิมก่อนแยกเป็น 3 แท็บ — เผื่อ bookmark เก่า
@bp.route("/news-report")
@login_required
def news_report():
    return redirect(url_for("reports.new_report", form_type="advance"))


def _split_choices(value):
    return [v.strip() for v in (value or "").split(",") if v.strip()]


def _prefill_form(form, item):
    """เติมค่าจากรายงานเดิมลงฟอร์ม (ใช้ตอนเปิดหน้าแก้ไขครั้งแรก)."""
    form.special_branch_province.data = item.special_branch_province
    form.title.data = item.title
    form.activity_types.data = _split_choices(item.activity_types)
    form.problem_group_types.data = _split_choices(item.problem_group_types)
    if item.event_datetime:
        form.event_date.data = item.event_datetime.date()
        form.event_time.data = item.event_datetime.time()
    if item.event_end_datetime:
        form.event_end_date.data = item.event_end_datetime.date()
        form.event_end_time.data = item.event_end_datetime.time()
    form.permit_status.data = item.permit_status
    form.permit_location.data = item.permit_location
    form.permit_duration_days.data = item.permit_duration_days
    form.location.data = item.location
    form.group_name.data = item.group_name
    form.leader_count.data = len(item.leaders)
    form.participant_count.data = len(item.people_of("participant"))
    form.supporter_count.data = len(item.people_of("supporter"))
    form.aff_net_count.data = len(item.people_of("affiliate", AFFILIATE_CATEGORIES[0]))
    form.aff_coord_count.data = len(item.people_of("affiliate", AFFILIATE_CATEGORIES[1]))
    form.aff_joint_count.data = len(item.people_of("affiliate", AFFILIATE_CATEGORIES[2]))
    form.org_party_count.data = len(item.people_of("related_org", RELATED_ORG_CATEGORIES[0]))
    form.org_ngo_count.data = len(item.people_of("related_org", RELATED_ORG_CATEGORIES[1]))
    form.org_gov_count.data = len(item.people_of("related_org", RELATED_ORG_CATEGORIES[2]))
    form.media_count.data = len(item.media_posts)
    form.mass_count.data = item.mass_count
    form.mass_members.data = item.mass_members
    form.mass_media.data = item.mass_media
    form.mass_others.data = item.mass_others
    form.activity_format.data = item.activity_format
    form.demands.data = item.demands
    form.activity_detail.data = item.activity_detail
    form.supporters.data = item.supporters
    form.affiliations.data = item.affiliations
    form.overnight_equipment_status.data = item.overnight_equipment_status
    form.overnight_equipment_detail.data = item.overnight_equipment_detail
    form.vehicle_status.data = item.vehicle_status
    form.vehicle_count.data = len(item.vehicles)
    form.other_info.data = item.other_info
    form.trend_assessment.data = item.trend_assessment
    form.considerations.data = item.considerations
    form.reporter_name.data = item.reporter_name
    form.reporter_phone.data = item.reporter_phone


def _fmt_dt(dt):
    """วัน-เวลากิจกรรมที่ผู้ใช้กรอกเอง (เวลาไทยอยู่แล้ว ไม่ต้องเลื่อนโซนเวลา)."""
    return dt.strftime("%d/%m/%Y %H:%M") if dt else "-"


def _person_lines(people, with_role=True):
    lines = []
    for i, p in enumerate(people):
        parts = [p.full_name]
        if p.group_name:
            parts.append(f"กลุ่ม/ตำแหน่ง: {p.group_name}")
        if with_role and p.role:
            parts.append(f"บทบาท: {p.role}")
        lines.append(f"{i + 1}. " + " — ".join(parts))
    return "\n".join(lines)


def _detail_rows(item):
    """(หัวข้อ, ค่า) ทุกช่องของรายงาน — ใช้ทั้งแสดงหน้ารายละเอียดและข้อความสำหรับปุ่ม copy."""
    leader_lines = []
    for i, leader in enumerate(item.leaders):
        parts = [leader.full_name]
        if leader.position:
            parts.append(f"ตำแหน่ง: {leader.position}")
        if leader.role:
            parts.append(f"บทบาท: {leader.role}")
        leader_lines.append(f"{i + 1}. " + " — ".join(parts))
    leaders = "\n".join(leader_lines) or "-"

    vehicle_lines = []
    for i, v in enumerate(item.vehicles):
        line = (
            f"คันที่ {i + 1}: {v.vehicle_type or '-'} ทะเบียน {v.plate_number or '-'} "
            f"จังหวัด {v.province or '-'} สี {v.color or '-'}"
        )
        if v.owner:
            line += f" เจ้าของ/ผู้ครอบครอง: {v.owner}"
        if v.usage:
            line += f" ใช้ทำ: {v.usage}"
        vehicle_lines.append(line)
    vehicles = "\n".join(vehicle_lines) or "-"

    equipment = item.overnight_equipment_status
    if item.overnight_equipment_detail:
        equipment += f" — {item.overnight_equipment_detail}"

    mass_parts = []
    if item.mass_members:
        mass_parts.append(f"สมาชิกกลุ่ม: {item.mass_members}")
    if item.mass_media:
        mass_parts.append(f"นักข่าว/สื่อ: {item.mass_media}")
    if item.mass_others:
        mass_parts.append(f"อื่นๆ: {item.mass_others}")

    trend_label = "แนวโน้มในอนาคต" if item.report_type == "closure" else "แนวโน้มสถานการณ์"

    rows = [
        ("ประเภทรายงาน", REPORT_TYPE_LABELS.get(item.report_type, item.report_type)),
        ("สันติบาล จว.", item.special_branch_province or "-"),
        ("ชื่อกิจกรรม", item.title),
        ("ประเภทกิจกรรม", item.activity_types or "-"),
        ("ประเภทกลุ่มปัญหา", item.problem_group_types or "-"),
        ("วันเวลานัดหมายทำกิจกรรม", _fmt_dt(item.event_datetime)),
        ("วันเวลาสิ้นสุดกิจกรรม", _fmt_dt(item.event_end_datetime)),
        ("การขออนุญาต", item.permit_status),
        ("ขออนุญาตที่ไหน", item.permit_location or "-"),
        ("ระยะเวลาทำกิจกรรม (วัน)", str(item.permit_duration_days) if item.permit_duration_days is not None else "-"),
        ("ชื่อกลุ่ม", item.group_name or "-"),
        ("แกนนำ", leaders),
    ]

    participants = item.people_of("participant")
    if participants:
        rows.append(("แนวร่วมหรือบุคคลสำคัญที่มาร่วมกิจกรรม", _person_lines(participants)))

    rows += [
        ("สถานที่นัดหมาย", item.location),
        ("จำนวนมวลชน", item.mass_count or "-"),
    ]
    if mass_parts:
        rows.append(("จำแนกมวลชน", "\n".join(mass_parts)))

    rows += [
        ("รูปแบบการจัดกิจกรรม", item.activity_format or "-"),
        ("ข้อเรียกร้อง/วัตถุประสงค์", item.demands),
    ]
    if item.activity_detail:
        rows.append(("รายละเอียดการทำกิจกรรม", item.activity_detail))

    supporters_people = item.people_of("supporter")
    if supporters_people:
        rows.append(("ผู้สนับสนุน/ผู้อยู่เบื้องหลัง", _person_lines(supporters_people)))
    elif item.supporters:
        rows.append(("ผู้สนับสนุน", item.supporters))
    else:
        rows.append(("ผู้สนับสนุน", "-"))

    affiliate_lines = []
    for category in AFFILIATE_CATEGORIES:
        entries = item.people_of("affiliate", category)
        for p in entries:
            line = f"{category}: {p.full_name}"
            if p.group_name:
                line += f" (กลุ่ม: {p.group_name})"
            affiliate_lines.append(line)
    affiliation_text = item.affiliations or ""
    combined_affiliations = "\n".join(filter(None, [affiliation_text, "\n".join(affiliate_lines)]))
    rows.append(("ความเชื่อมโยง/ความเกี่ยวข้องกับบุคคลหรือองค์กรอื่นๆ", combined_affiliations or "-"))

    org_lines = []
    for category in RELATED_ORG_CATEGORIES:
        for p in item.people_of("related_org", category):
            line = f"{category}: {p.full_name}"
            if p.role:
                line += f" — บทบาท: {p.role}"
            org_lines.append(line)
    if org_lines:
        rows.append(("กลุ่มการเมือง องค์กร หรือบุคคลอื่นๆ ที่มาเกี่ยวข้อง", "\n".join(org_lines)))

    if item.media_posts:
        media_lines = [
            f"{i + 1}. {m.page_name} — Like: {m.likes or '-'}, แชร์: {m.shares or '-'}"
            for i, m in enumerate(item.media_posts)
        ]
        rows.append(("การเผยแพร่กิจกรรมทางสื่อออนไลน์และกระแสสนใจ", "\n".join(media_lines)))

    rows += [
        ("สัมภาระค้างแรม/อุปกรณ์", equipment),
        ("ยานพาหนะ", item.vehicle_status if item.vehicle_status == "ไม่มี" else f"มี\n{vehicles}"),
        ("ข้อมูลน่าสนใจอื่นๆ", item.other_info or "-"),
        (trend_label, item.trend_assessment or "-"),
        ("ข้อพิจารณา", item.considerations or "-"),
        ("ผู้รายงาน", item.reporter_name or "-"),
        ("เบอร์ติดต่อ", item.reporter_phone or "-"),
    ]
    return rows


@bp.route("/<int:report_id>")
@login_required
def view_report(report_id):
    item = NewsReport.query.get_or_404(report_id)
    rows = _detail_rows(item)

    thai_created = item.created_at + timedelta(hours=7)
    recorder = item.created_by.full_name if item.created_by else "-"
    copy_lines = ["รายงานข่าว"]
    copy_lines += [f"{label}: {value}" for label, value in rows]
    copy_lines.append(f"บันทึกเมื่อ: {thai_created.strftime('%d/%m/%Y %H:%M')} โดย {recorder}")
    copy_text = "\n".join(copy_lines)

    return render_template(
        "reports/detail.html",
        item=item,
        rows=rows,
        copy_text=copy_text,
    )


@bp.route("/<int:report_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_report(report_id):
    item = NewsReport.query.get_or_404(report_id)
    form_type = item.report_type if item.report_type in REPORT_FORM_TITLES else "incident"
    form = NewsReportForm()

    if form.validate_on_submit():
        for key, value in _fields_from_form(form).items():
            setattr(item, key, value)
        _attach_children(item, form, form_type)
        db.session.commit()

        synced = sheets_sync.sync_report(current_app._get_current_object(), item)
        if sheets_sync.is_configured(current_app.config) and not synced:
            flash("แก้ไขเรียบร้อย แต่ sync ขึ้น Google Sheets ไม่สำเร็จ (ดู log)", "warning")
        else:
            flash("แก้ไขรายงานข่าวเรียบร้อยแล้ว", "success")
        return redirect(url_for("reports.view_report", report_id=item.id))

    if request.method == "GET":
        _prefill_form(form, item)
        rows = _rows_from_item(item)
    else:
        rows = _rows_from_request()

    return _render_report_form(form, form_type, rows, edit_item=item)
