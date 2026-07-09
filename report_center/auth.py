from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .extensions import db
from .forms import LoginForm, RegisterForm
from .models import LoginLog, User

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _default_landing_url(user):
    return url_for("reports.dashboard") if user.is_admin else url_for("reports.advance")


def _client_ip():
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or ""


def _record_login(user_id, username_attempted, success, reason):
    log = LoginLog(
        user_id=user_id,
        username_attempted=username_attempted,
        success=success,
        reason=reason,
        ip_address=_client_ip(),
        user_agent=request.headers.get("User-Agent", "")[:255],
    )
    db.session.add(log)
    db.session.commit()


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(_default_landing_url(current_user))

    form = RegisterForm()
    if form.validate_on_submit():
        existing = User.query.filter_by(username=form.username.data).first()
        if existing:
            flash("มีชื่อผู้ใช้นี้ในระบบแล้ว กรุณาเลือกชื่ออื่น", "danger")
        else:
            user = User(
                username=form.username.data,
                full_name=form.full_name.data,
                role="user",
                is_approved=False,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash("สมัครสมาชิกสำเร็จ กรุณารอผู้ดูแลระบบอนุมัติบัญชีก่อนเข้าสู่ระบบ", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(_default_landing_url(current_user))

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(form.password.data):
            _record_login(None, username, False, "invalid_credentials")
            flash("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง", "danger")
        elif not user.is_approved:
            _record_login(user.id, username, False, "pending_approval")
            flash("บัญชีนี้ยังไม่ได้รับการอนุมัติจากผู้ดูแลระบบ", "warning")
        else:
            login_user(user)
            _record_login(user.id, username, True, None)
            flash(f"ยินดีต้อนรับ {user.full_name}", "success")
            next_url = request.args.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(_default_landing_url(user))
    return render_template("auth/login.html", form=form)


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("ออกจากระบบเรียบร้อยแล้ว", "info")
    return redirect(url_for("auth.login"))
