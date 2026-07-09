from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import current_user, login_required

from .admin import admin_required
from .extensions import db
from .forms import (
    AdvanceNewsForm,
    GeneralNewsForm,
    NewsClosureForm,
    SituationReportForm,
)
from .models import (
    REPORT_CATEGORIES,
    AdvanceNews,
    GeneralNews,
    NewsClosure,
    SituationReport,
)

bp = Blueprint("reports", __name__, url_prefix="/reports")


@bp.route("/")
@login_required
@admin_required
def dashboard():
    counts = {key: meta["model"].query.count() for key, meta in REPORT_CATEGORIES.items()}
    recent = {
        key: meta["model"].query.order_by(meta["model"].created_at.desc()).limit(5).all()
        for key, meta in REPORT_CATEGORIES.items()
    }
    return render_template(
        "reports/dashboard.html", counts=counts, recent=recent, categories=REPORT_CATEGORIES
    )


@bp.route("/advance", methods=["GET", "POST"])
@login_required
def advance():
    form = AdvanceNewsForm()
    if form.validate_on_submit():
        item = AdvanceNews(
            title=form.title.data,
            event_datetime=form.event_datetime.data,
            location=form.location.data,
            description=form.description.data,
            target_group=form.target_group.data,
            source=form.source.data,
            reliability_level=form.reliability_level.data,
            priority_level=form.priority_level.data,
            preventive_measures=form.preventive_measures.data,
            related_agency=form.related_agency.data,
            created_by_id=current_user.id,
        )
        db.session.add(item)
        db.session.commit()
        flash("บันทึกข่าวล่วงหน้าเรียบร้อยแล้ว", "success")
        return redirect(url_for("reports.advance"))

    return render_template("reports/advance.html", form=form)


@bp.route("/closure", methods=["GET", "POST"])
@login_required
def closure():
    form = NewsClosureForm()
    form.related_advance_id.choices = [(0, "— ไม่ผูกกับข่าวล่วงหน้า —")] + [
        (a.id, f"#{a.id} {a.title}") for a in AdvanceNews.query.order_by(AdvanceNews.created_at.desc()).all()
    ]
    if form.validate_on_submit():
        related_id = form.related_advance_id.data or None
        item = NewsClosure(
            title=form.title.data,
            related_advance_id=related_id if related_id else None,
            reference_note=form.reference_note.data,
            closure_date=form.closure_date.data,
            result_status=form.result_status.data,
            operation_result=form.operation_result.data,
            responsible_person=form.responsible_person.data,
            responsible_agency=form.responsible_agency.data,
            notes=form.notes.data,
            created_by_id=current_user.id,
        )
        db.session.add(item)
        db.session.commit()
        flash("บันทึกการปิดข่าวเรียบร้อยแล้ว", "success")
        return redirect(url_for("reports.closure"))

    return render_template("reports/closure.html", form=form)


@bp.route("/situation", methods=["GET", "POST"])
@login_required
def situation():
    form = SituationReportForm()
    if form.validate_on_submit():
        item = SituationReport(
            title=form.title.data,
            incident_datetime=form.incident_datetime.data,
            location=form.location.data,
            situation_type=form.situation_type.data,
            description=form.description.data,
            severity_level=form.severity_level.data,
            impact=form.impact.data,
            initial_action=form.initial_action.data,
            related_agency=form.related_agency.data,
            current_status=form.current_status.data,
            created_by_id=current_user.id,
        )
        db.session.add(item)
        db.session.commit()
        flash("บันทึกรายงานสถานการณ์ข่าวเรียบร้อยแล้ว", "success")
        return redirect(url_for("reports.situation"))

    return render_template("reports/situation.html", form=form)


@bp.route("/general", methods=["GET", "POST"])
@login_required
def general():
    form = GeneralNewsForm()
    if form.validate_on_submit():
        item = GeneralNews(
            title=form.title.data,
            news_date=form.news_date.data,
            source=form.source.data,
            summary=form.summary.data,
            area=form.area.data,
            category_tag=form.category_tag.data,
            notes=form.notes.data,
            created_by_id=current_user.id,
        )
        db.session.add(item)
        db.session.commit()
        flash("บันทึกข่าวทั่วไปเรียบร้อยแล้ว", "success")
        return redirect(url_for("reports.general"))

    return render_template("reports/general.html", form=form)
