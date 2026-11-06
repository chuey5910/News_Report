"""หมวด "จัดการระบบ" — เนื้อหาเปลี่ยนตามระดับของคนที่ล็อกอิน

- เจ้าหน้าที่      → งานของฉัน (รายงานที่ตัวเองบันทึก แยกสถานะ งานที่ถูกส่งกลับขึ้นบนสุด)
- หัวหน้า          → ตรวจยืนยันรายงานของเจ้าหน้าที่สังกัดเดียวกัน (ค้างนานสุดอยู่บน)
- แอดมิน           → ตรวจยืนยันทุกสังกัด + บันทึกการใช้งาน (จัดการผู้ใช้/ประวัติเข้าสู่ระบบอยู่ใน admin.py)
"""

from datetime import datetime, timedelta

from flask import Blueprint, abort, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import or_

from .admin import admin_required
from .audit import ACTION_LABELS
from .models import (
    STATUS_PENDING,
    STATUS_RETURNED,
    STATUS_VERIFIED,
    AuditLog,
    NewsReport,
    User,
)

bp = Blueprint("manage", __name__, url_prefix="/manage")


def _thai_now():
    return datetime.utcnow() + timedelta(hours=7)


def waiting_label(submitted_at):
    """ค้างมานานแค่ไหน — "วันนี้" / "N วัน" (นับตามวันไทย)."""
    if not submitted_at:
        return "-", 0
    days = (_thai_now().date() - (submitted_at + timedelta(hours=7)).date()).days
    return ("วันนี้" if days <= 0 else f"{days} วัน"), max(days, 0)


def pending_query_for(user):
    """รายงานรอยืนยันที่ผู้ใช้คนนี้มีสิทธิ์ตรวจ — หัวหน้าเห็นเฉพาะสังกัดตัวเอง แอดมินเห็นหมด."""
    query = NewsReport.query.filter(NewsReport.status == STATUS_PENDING)
    if not user.is_admin:
        query = query.join(User, NewsReport.created_by_id == User.id).filter(User.unit == user.unit)
    return query


def pending_count_for(user):
    if user.is_admin or user.is_chief:
        return pending_query_for(user).count()
    return 0


def returned_count_for(user):
    """เจ้าหน้าที่: จำนวนงานของตัวเองที่ถูกส่งกลับ (ป้ายแดงบนเมนู)."""
    return NewsReport.query.filter(
        NewsReport.created_by_id == user.id, NewsReport.status == STATUS_RETURNED
    ).count()


@bp.route("/verify")
@login_required
def verify_queue():
    if not (current_user.is_admin or current_user.is_chief):
        abort(403)
    pending = pending_query_for(current_user).order_by(NewsReport.submitted_at.asc(), NewsReport.id.asc()).all()
    # งานที่ส่งกลับไปแล้วรอเจ้าหน้าที่แก้ (ให้หัวหน้าเห็นว่าค้างอยู่ที่ใคร)
    returned_q = NewsReport.query.filter(NewsReport.status == STATUS_RETURNED)
    if not current_user.is_admin:
        returned_q = returned_q.join(User, NewsReport.created_by_id == User.id).filter(User.unit == current_user.unit)
    returned = returned_q.order_by(NewsReport.returned_at.desc()).all()

    rows = []
    for item in pending:
        label, days = waiting_label(item.submitted_at)
        rows.append({"item": item, "wait": label, "hot": days >= 2})

    # สังกัดที่ยังไม่มีหัวหน้า (แอดมินต้องยืนยันแทน) — แสดงเป็นป้ายเตือน
    units_without_chief = []
    if current_user.is_admin:
        chief_units = {u.unit for u in User.query.filter_by(position="chief", is_approved=True).all()}
        for item in pending:
            unit = item.author_unit
            if unit and unit not in chief_units and unit not in units_without_chief:
                units_without_chief.append(unit)

    return render_template(
        "manage/verify.html",
        rows=rows,
        returned=returned,
        units_without_chief=units_without_chief,
        scope_label=None if current_user.is_admin else current_user.unit,
    )


@bp.route("/mine")
@login_required
def my_work():
    """งานของฉัน — รายงานที่ตัวเองบันทึก ส่งกลับแก้ไขขึ้นบนสุด แล้วรอยืนยัน แล้วยืนยันแล้ว."""
    order = {STATUS_RETURNED: 0, STATUS_PENDING: 1, STATUS_VERIFIED: 2}
    items = (
        NewsReport.query.filter(NewsReport.created_by_id == current_user.id)
        .order_by(NewsReport.created_at.desc())
        .limit(300)
        .all()
    )
    items.sort(key=lambda r: (order.get(r.status, 9), -(r.created_at.timestamp())))
    counts = {key: sum(1 for r in items if r.status == key) for key in order}
    return render_template("manage/mine.html", items=items, counts=counts)


@bp.route("/audit")
@login_required
@admin_required
def audit_log():
    page = request.args.get("page", 1, type=int)
    q = (request.args.get("q") or "").strip()
    action = (request.args.get("action") or "").strip()
    query = AuditLog.query
    if q:
        like = f"%{q}%"
        query = query.filter(or_(AuditLog.username.ilike(like), AuditLog.detail.ilike(like)))
    if action in ACTION_LABELS:
        query = query.filter(AuditLog.action == action)
    pagination = query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=60, error_out=False)
    return render_template(
        "manage/audit.html",
        pagination=pagination,
        q=q,
        action=action,
        action_labels=ACTION_LABELS,
    )
