from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from . import audit
from .extensions import db
from .models import DESK_UNIT, POSITION_LABELS, SPECIAL_BRANCH_PROVINCES, LoginLog, User

UNIT_CHOICES = [f"ส.จว.{p}" for p in SPECIAL_BRANCH_PROVINCES] + [DESK_UNIT]

bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


@bp.route("/users")
@login_required
@admin_required
def users():
    # รออนุมัติขึ้นก่อน แล้วเรียงตามสังกัด
    all_users = User.query.order_by(User.is_approved.asc(), User.unit.asc(), User.position.desc(), User.full_name.asc()).all()
    return render_template(
        "admin/users.html", users=all_users, unit_choices=UNIT_CHOICES, position_labels=POSITION_LABELS
    )


@bp.route("/users/<int:user_id>/approve", methods=["POST"])
@login_required
@admin_required
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    _apply_unit_position(user)      # แอดมินปรับสังกัด/ตำแหน่งที่ขอมาได้ก่อนอนุมัติ
    user.is_approved = True
    db.session.commit()
    audit.log("approve_user", "user", user.id, f"{user.username} → {user.level_label}")
    flash(f"อนุมัติบัญชี {user.username} เป็น {user.level_label} เรียบร้อยแล้ว", "success")
    return redirect(url_for("admin.users"))


@bp.route("/users/<int:user_id>/revoke", methods=["POST"])
@login_required
@admin_required
def revoke_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("ไม่สามารถระงับบัญชีของตนเองได้", "danger")
        return redirect(url_for("admin.users"))
    user.is_approved = False
    db.session.commit()
    audit.log("revoke_user", "user", user.id, user.username)
    flash(f"ระงับการใช้งานบัญชี {user.username} แล้ว", "warning")
    return redirect(url_for("admin.users"))


def _apply_unit_position(user):
    """อ่านสังกัด/ตำแหน่ง/แอดมิน จากฟอร์มแถวของผู้ใช้คนนั้น (ถ้าส่งมา) — คืน True เมื่อมีการเปลี่ยน."""
    changed = False
    unit = request.form.get("unit")
    position = request.form.get("position")
    role = request.form.get("role")
    if unit in UNIT_CHOICES and unit != user.unit:
        user.unit = unit
        changed = True
    if position in POSITION_LABELS and position != user.position:
        user.position = position
        changed = True
    if role in ("admin", "user") and role != user.role:
        if user.id == current_user.id and role != "admin":
            flash("ไม่สามารถลดสิทธิ์บัญชีของตนเองได้", "danger")
        else:
            user.role = role
            changed = True
    return changed


@bp.route("/users/<int:user_id>/update", methods=["POST"])
@login_required
@admin_required
def update_user(user_id):
    """แอดมินเปลี่ยนสังกัด / ตำแหน่ง / สิทธิ์แอดมิน ของผู้ใช้."""
    user = User.query.get_or_404(user_id)
    before = user.level_label
    if _apply_unit_position(user):
        db.session.commit()
        audit.log("update_user", "user", user.id, f"{user.username}: {before} → {user.level_label}")
        flash(f"บันทึก {user.username} เป็น {user.level_label} แล้ว", "success")
    else:
        flash("ไม่มีอะไรเปลี่ยนแปลง", "info")
    return redirect(url_for("admin.users"))


@bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@login_required
@admin_required
def reset_user_password(user_id):
    """ตั้งรหัสผ่านใหม่ให้ผู้ใช้ที่ลืมรหัส — ระบบไม่มีอีเมล จึงต้องให้ admin ตั้งให้แล้วแจ้งเจ้าตัว"""
    user = User.query.get_or_404(user_id)
    new_password = request.form.get("new_password") or ""
    if len(new_password) < 8:
        flash("รหัสผ่านใหม่ต้องยาวอย่างน้อย 8 ตัวอักษร", "danger")
        return redirect(url_for("admin.users"))
    user.set_password(new_password)
    db.session.commit()
    audit.log("reset_password", "user", user.id, user.username)
    flash(
        f"ตั้งรหัสผ่านใหม่ให้ {user.username} ({user.full_name}) แล้ว — "
        "แจ้งรหัสนี้ให้เจ้าตัวแล้วบอกให้เข้าไปเปลี่ยนเป็นรหัสของตัวเองที่เมนู 'เปลี่ยนรหัสผ่าน'",
        "success",
    )
    return redirect(url_for("admin.users"))


@bp.route("/login-logs")
@login_required
@admin_required
def login_logs():
    page = request.args.get("page", 1, type=int)
    pagination = LoginLog.query.order_by(LoginLog.timestamp.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    return render_template("admin/login_logs.html", pagination=pagination)
