from datetime import datetime, time as time_cls, timedelta

from flask import Blueprint, current_app, render_template, redirect, request, url_for, flash
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from . import sheets_sync
from .admin import admin_required
from .extensions import db
from .forms import NewsReportForm
from .models import (
    REPORT_TYPE_CHOICES,
    REPORT_TYPE_LABELS,
    SPECIAL_BRANCH_PROVINCES,
    NewsReport,
    NewsReportLeader,
    NewsReportVehicle,
)

bp = Blueprint("reports", __name__, url_prefix="/reports")


def _combine_date_time(date_val, time_val):
    if date_val is None:
        return None
    return datetime.combine(date_val, time_val or time_cls.min)


def _fields_from_form(form):
    permit_granted = form.permit_status.data == "มีการขออนุญาต"
    equipment_present = form.overnight_equipment_status.data == "มี"

    return {
        "report_type": form.report_type.data,
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
        "activity_format": form.activity_format.data,
        "demands": form.demands.data,
        "supporters": form.supporters.data,
        "affiliations": form.affiliations.data,
        "overnight_equipment_status": form.overnight_equipment_status.data,
        "overnight_equipment_detail": form.overnight_equipment_detail.data if equipment_present else None,
        "vehicle_status": form.vehicle_status.data,
        "other_info": form.other_info.data,
        "trend_assessment": form.trend_assessment.data,
        "reporter_name": form.reporter_name.data,
        "reporter_phone": form.reporter_phone.data,
        "created_by_id": current_user.id,
    }


def _leaders_from_request():
    return [name.strip() for name in request.form.getlist("leader_name") if name.strip()]


def _vehicles_from_request():
    vehicle_types = request.form.getlist("vehicle_type")
    plate_numbers = request.form.getlist("vehicle_plate")
    provinces = request.form.getlist("vehicle_province")
    colors = request.form.getlist("vehicle_color")
    rows = []
    for vtype, plate, province, color in zip(vehicle_types, plate_numbers, provinces, colors):
        if any(v.strip() for v in (vtype, plate, province, color)):
            rows.append(
                {"vehicle_type": vtype.strip(), "plate_number": plate.strip(), "province": province.strip(), "color": color.strip()}
            )
    return rows


def _submitted_dynamic_fields():
    """For re-rendering the form with previously-entered leader/vehicle rows after a validation error."""
    if request.method != "POST":
        return [], []
    leaders = request.form.getlist("leader_name")
    vehicles = []
    vehicle_types = request.form.getlist("vehicle_type")
    plate_numbers = request.form.getlist("vehicle_plate")
    provinces = request.form.getlist("vehicle_province")
    colors = request.form.getlist("vehicle_color")
    for vtype, plate, province, color in zip(vehicle_types, plate_numbers, provinces, colors):
        vehicles.append({"vehicle_type": vtype, "plate_number": plate, "province": province, "color": color})
    return leaders, vehicles


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
        query = query.filter(
            or_(
                NewsReport.title.ilike(like),
                NewsReport.group_name.ilike(like),
                NewsReport.location.ilike(like),
                NewsReport.demands.ilike(like),
                NewsReport.other_info.ilike(like),
                NewsReport.reporter_name.ilike(like),
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

    return render_template(
        "reports/dashboard.html",
        counts=counts,
        results=results,
        analysis_rows=analysis_rows,
        report_type_labels=REPORT_TYPE_LABELS,
        report_type_choices=REPORT_TYPE_CHOICES,
        provinces=SPECIAL_BRANCH_PROVINCES,
        q=q,
        province=province,
        rtype=rtype,
        filtered=bool(q or province or rtype),
    )


def _split_choices(value):
    return [v.strip() for v in (value or "").split(",") if v.strip()]


def _prefill_form(form, item):
    """เติมค่าจากรายงานเดิมลงฟอร์ม (ใช้ตอนเปิดหน้าแก้ไขครั้งแรก)."""
    form.report_type.data = item.report_type
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
    form.mass_count.data = item.mass_count
    form.activity_format.data = item.activity_format
    form.demands.data = item.demands
    form.supporters.data = item.supporters
    form.affiliations.data = item.affiliations
    form.overnight_equipment_status.data = item.overnight_equipment_status
    form.overnight_equipment_detail.data = item.overnight_equipment_detail
    form.vehicle_status.data = item.vehicle_status
    form.vehicle_count.data = len(item.vehicles)
    form.other_info.data = item.other_info
    form.trend_assessment.data = item.trend_assessment
    form.reporter_name.data = item.reporter_name
    form.reporter_phone.data = item.reporter_phone


def _fmt_dt(dt):
    """วัน-เวลากิจกรรมที่ผู้ใช้กรอกเอง (เวลาไทยอยู่แล้ว ไม่ต้องเลื่อนโซนเวลา)."""
    return dt.strftime("%d/%m/%Y %H:%M") if dt else "-"


def _detail_rows(item):
    """(หัวข้อ, ค่า) ทุกช่องของรายงาน — ใช้ทั้งแสดงหน้ารายละเอียดและข้อความสำหรับปุ่ม copy."""
    leaders = "\n".join(f"{i + 1}. {l.full_name}" for i, l in enumerate(item.leaders)) or "-"
    vehicles = (
        "\n".join(
            f"คันที่ {i + 1}: {v.vehicle_type or '-'} ทะเบียน {v.plate_number or '-'} "
            f"จังหวัด {v.province or '-'} สี {v.color or '-'}"
            for i, v in enumerate(item.vehicles)
        )
        or "-"
    )
    equipment = item.overnight_equipment_status
    if item.overnight_equipment_detail:
        equipment += f" — {item.overnight_equipment_detail}"

    return [
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
        ("สถานที่นัดหมาย", item.location),
        ("จำนวนมวลชน", item.mass_count or "-"),
        ("รูปแบบการจัดกิจกรรม", item.activity_format or "-"),
        ("ข้อเรียกร้อง/วัตถุประสงค์", item.demands),
        ("ผู้สนับสนุน", item.supporters or "-"),
        ("ความเชื่อมโยงกับบุคคลหรือองค์กรอื่นๆ", item.affiliations or "-"),
        ("สัมภาระค้างแรม/อุปกรณ์", equipment),
        ("ยานพาหนะ", item.vehicle_status if item.vehicle_status == "ไม่มี" else f"มี\n{vehicles}"),
        ("ข้อมูลน่าสนใจอื่นๆ", item.other_info or "-"),
        ("แนวโน้ม/ข้อพิจารณา", item.trend_assessment or "-"),
        ("ผู้รายงาน", item.reporter_name or "-"),
        ("เบอร์ติดต่อ", item.reporter_phone or "-"),
    ]


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
        report_type_labels=REPORT_TYPE_LABELS,
    )


@bp.route("/<int:report_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_report(report_id):
    item = NewsReport.query.get_or_404(report_id)
    form = NewsReportForm()

    if form.validate_on_submit():
        fields = _fields_from_form(form)
        fields.pop("created_by_id")  # คงผู้บันทึกคนเดิมไว้
        for key, value in fields.items():
            setattr(item, key, value)

        item.leaders.clear()
        for full_name in _leaders_from_request():
            item.leaders.append(NewsReportLeader(full_name=full_name))

        item.vehicles.clear()
        if form.vehicle_status.data == "มี":
            for row in _vehicles_from_request():
                item.vehicles.append(NewsReportVehicle(**row))

        db.session.commit()

        synced = sheets_sync.sync_report(current_app._get_current_object(), item)
        if sheets_sync.is_configured(current_app.config) and not synced:
            flash("แก้ไขเรียบร้อย แต่ sync ขึ้น Google Sheets ไม่สำเร็จ (ดู log)", "warning")
        else:
            flash("แก้ไขรายงานข่าวเรียบร้อยแล้ว", "success")
        return redirect(url_for("reports.view_report", report_id=item.id))

    if request.method == "GET":
        _prefill_form(form, item)
        submitted_leaders = [leader.full_name for leader in item.leaders]
        submitted_vehicles = [
            {
                "vehicle_type": v.vehicle_type,
                "plate_number": v.plate_number,
                "province": v.province,
                "color": v.color,
            }
            for v in item.vehicles
        ]
    else:
        submitted_leaders, submitted_vehicles = _submitted_dynamic_fields()

    return render_template(
        "reports/news_report.html",
        form=form,
        submitted_leaders=submitted_leaders,
        submitted_vehicles=submitted_vehicles,
        edit_item=item,
    )


@bp.route("/news-report", methods=["GET", "POST"])
@login_required
def news_report():
    form = NewsReportForm()
    if form.validate_on_submit():
        item = NewsReport(**_fields_from_form(form))

        for full_name in _leaders_from_request():
            item.leaders.append(NewsReportLeader(full_name=full_name))

        if form.vehicle_status.data == "มี":
            for row in _vehicles_from_request():
                item.vehicles.append(NewsReportVehicle(**row))

        db.session.add(item)
        db.session.commit()

        # Best-effort sync to Google Sheets (never blocks or fails the save)
        synced = sheets_sync.sync_report(current_app._get_current_object(), item)
        if sheets_sync.is_configured(current_app.config) and not synced:
            flash("บันทึกเรียบร้อย แต่ sync ขึ้น Google Sheets ไม่สำเร็จ (ดู log) — ข้อมูลถูกเก็บในระบบแล้ว", "warning")
        else:
            flash("บันทึกรายงานข่าวเรียบร้อยแล้ว", "success")
        return redirect(url_for("reports.news_report"))

    submitted_leaders, submitted_vehicles = _submitted_dynamic_fields()
    return render_template(
        "reports/news_report.html",
        form=form,
        submitted_leaders=submitted_leaders,
        submitted_vehicles=submitted_vehicles,
    )
