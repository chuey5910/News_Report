from datetime import datetime, time as time_cls

from flask import Blueprint, current_app, render_template, redirect, request, url_for, flash
from flask_login import current_user, login_required

from . import sheets_sync
from .admin import admin_required
from .extensions import db
from .forms import NewsReportForm
from .models import REPORT_TYPE_LABELS, NewsReport, NewsReportLeader, NewsReportVehicle

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
@admin_required
def dashboard():
    counts = {
        "total": NewsReport.query.count(),
        "advance": NewsReport.query.filter_by(report_type="advance").count(),
        "closure": NewsReport.query.filter_by(report_type="closure").count(),
        "incident": NewsReport.query.filter_by(report_type="incident").count(),
        "general": NewsReport.query.filter_by(report_type="general").count(),
    }
    recent = NewsReport.query.order_by(NewsReport.created_at.desc()).limit(10).all()
    return render_template(
        "reports/dashboard.html", counts=counts, recent=recent, report_type_labels=REPORT_TYPE_LABELS
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
