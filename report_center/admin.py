from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .extensions import db
from .models import LoginLog, User

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
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=all_users)


@bp.route("/users/<int:user_id>/approve", methods=["POST"])
@login_required
@admin_required
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_approved = True
    db.session.commit()
    flash(f"อนุมัติบัญชีผู้ใช้ {user.username} เรียบร้อยแล้ว", "success")
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
    flash(f"ระงับการใช้งานบัญชี {user.username} แล้ว", "warning")
    return redirect(url_for("admin.users"))


@bp.route("/users/<int:user_id>/role", methods=["POST"])
@login_required
@admin_required
def set_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get("role")
    if new_role not in ("admin", "user"):
        abort(400)
    if user.id == current_user.id and new_role != "admin":
        flash("ไม่สามารถลดสิทธิ์บัญชีของตนเองได้", "danger")
        return redirect(url_for("admin.users"))
    user.role = new_role
    db.session.commit()
    flash(f"เปลี่ยนสิทธิ์ผู้ใช้ {user.username} เป็น {new_role} แล้ว", "success")
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
