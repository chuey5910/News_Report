from datetime import datetime, timedelta

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .extensions import db
from .forms import LoginForm, RegisterForm
from .models import LoginLog, User

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _recent_failed_count(username, ip):
    """Count failed login attempts for this username OR this IP within the lockout window.
    Used to throttle brute-force attempts (counting from the last successful login resets it)."""
    window_start = datetime.utcnow() - timedelta(minutes=current_app.config["LOGIN_LOCKOUT_MINUTES"])
    q = LoginLog.query.filter(LoginLog.timestamp >= window_start)
    q = q.filter(
        db.or_(LoginLog.username_attempted == username, LoginLog.ip_address == ip)
    )
    attempts = q.order_by(LoginLog.timestamp.desc()).all()
    failed = 0
    for a in attempts:
        if a.success:
            break  # a success within the window clears the streak
        failed += 1
    return failed


def _is_locked_out(username, ip):
    return _recent_failed_count(username, ip) >= current_app.config["LOGIN_MAX_FAILED_ATTEMPTS"]


def _default_landing_url(user):
    return url_for("reports.dashboard") if user.is_admin else url_for("reports.new_report", form_type="advance")


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
        ip = _client_ip()

        if _is_locked_out(username, ip):
            _record_login(None, username, False, "locked_out")
            flash(
                f"พยายามเข้าสู่ระบบผิดหลายครั้งเกินไป — ถูกล็อกชั่วคราว "
                f"{current_app.config['LOGIN_LOCKOUT_MINUTES']} นาที กรุณาลองใหม่ภายหลัง",
                "danger",
            )
            return render_template("auth/login.html", form=form)

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
