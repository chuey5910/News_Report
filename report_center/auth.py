from datetime import datetime, timedelta

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from . import audit
from .extensions import db
from .forms import ChangePasswordForm, LoginForm, RegisterForm
from .models import LoginLog, User

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _recent_failed_count(username):
    """นับจำนวนครั้งที่กรอกรหัสผิดติดกันของ "ชื่อผู้ใช้นี้" ในช่วงเวลาที่กำหนด

    นับแยกตามชื่อผู้ใช้เท่านั้น ไม่นับรวม IP — เพราะผู้ใช้ทุกคนเข้าผ่าน Tailscale
    ออกมาที่ IP เดียวกัน ถ้านับรวม IP คนหนึ่งกรอกผิดจะทำให้ทุกคนถูกล็อกไปด้วย
    (การเข้าสู่ระบบสำเร็จ 1 ครั้งจะล้างสถิติที่นับไว้)
    """
    window_start = datetime.utcnow() - timedelta(minutes=current_app.config["LOGIN_LOCKOUT_MINUTES"])
    attempts = (
        LoginLog.query.filter(LoginLog.timestamp >= window_start)
        .filter(LoginLog.username_attempted == username)
        .order_by(LoginLog.timestamp.desc())
        .all()
    )
    failed = 0
    for a in attempts:
        if a.success:
            break  # a success within the window clears the streak
        failed += 1
    return failed


def _is_locked_out(username):
    return _recent_failed_count(username) >= current_app.config["LOGIN_MAX_FAILED_ATTEMPTS"]


def _default_landing_url(user):
    # admin เห็นแผนที่สถานการณ์ก่อน / หัวหน้าเห็นคิวงานรอตรวจ / เจ้าหน้าที่เข้าหน้าบันทึกข่าวล่วงหน้า
    if user.is_admin:
        return url_for("reports.situation_map")
    if user.is_chief:
        return url_for("manage.verify_queue")
    return url_for("reports.new_report", form_type="advance")


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
                unit=form.unit.data,
                position=form.position.data,
                is_approved=False,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            audit.log("register", "user", user.id, f"ขอเป็น {user.level_label}", user=user)
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

        if _is_locked_out(username):
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
            # remember=False + ไม่ตั้ง permanent → คุกกี้หายเมื่อปิดเบราว์เซอร์ (เท่าที่เครื่องยอม)
            login_user(user, remember=False)
            session.permanent = False
            now = datetime.utcnow().timestamp()
            session["login_at"] = now
            session["last_seen"] = now
            _record_login(user.id, username, True, None)
            audit.log("login", "session", None, user.level_label, user=user)
            flash(f"ยินดีต้อนรับ {user.full_name}", "success")
            next_url = request.args.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(_default_landing_url(user))
    return render_template("auth/login.html", form=form)


@bp.route("/logout")
@login_required
def logout():
    audit.log("logout", "session", None, request.args.get("reason") or None)
    logout_user()
    session.clear()
    flash("ออกจากระบบเรียบร้อยแล้ว", "info")
    return redirect(url_for("auth.login"))


@bp.route("/ping", methods=["POST"])
def ping():
    """หน้าเว็บส่งมาเป็นระยะขณะผู้ใช้ยังขยับอยู่ (พิมพ์/เลื่อน) เพื่อต่ออายุ 30 นาที — ตอบเวลาที่เหลือ."""
    if not current_user.is_authenticated:
        return jsonify({"ok": False}), 401
    now = datetime.utcnow().timestamp()
    session["last_seen"] = now
    idle = current_app.config["IDLE_TIMEOUT_MINUTES"] * 60
    absolute = current_app.config["MAX_SESSION_HOURS"] * 3600
    remaining = min(idle, int(session.get("login_at", now) + absolute - now))
    return jsonify({"ok": True, "remaining": max(remaining, 0)})


def enforce_session_limits():
    """เรียกก่อนทุกคำขอ: ไม่ขยับเกิน IDLE_TIMEOUT_MINUTES หรือเกิน MAX_SESSION_HOURS → ออกจากระบบ."""
    if not current_user.is_authenticated:
        return None
    now = datetime.utcnow().timestamp()
    idle = current_app.config["IDLE_TIMEOUT_MINUTES"] * 60
    absolute = current_app.config["MAX_SESSION_HOURS"] * 3600
    login_at = session.get("login_at")
    last_seen = session.get("last_seen")
    if login_at is None or last_seen is None:          # ล็อกอินค้างมาจากระบบรุ่นก่อน
        session["login_at"] = session["last_seen"] = now
        return None
    reason = None
    if now - last_seen > idle:
        reason = f"ไม่มีความเคลื่อนไหวเกิน {current_app.config['IDLE_TIMEOUT_MINUTES']} นาที"
    elif now - login_at > absolute:
        reason = f"ล็อกอินครบ {current_app.config['MAX_SESSION_HOURS']} ชั่วโมง"
    if reason:
        audit.log("auto_logout", "session", None, reason)
        logout_user()
        session.clear()
        if request.endpoint == "auth.ping" or request.path.startswith("/api/"):
            return jsonify({"ok": False, "reason": reason}), 401
        flash(f"ออกจากระบบอัตโนมัติ — {reason} กรุณาเข้าสู่ระบบใหม่", "warning")
        return redirect(url_for("auth.login", next=request.full_path if request.method == "GET" else None))
    if request.endpoint != "auth.ping":
        session["last_seen"] = now
    return None


@bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    """ผู้ใช้เปลี่ยนรหัสผ่านของตัวเอง — ใช้หลัง admin ตั้งรหัสชั่วคราวให้ หรือเมื่ออยากเปลี่ยนเอง"""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            _record_login(current_user.id, current_user.username, False, "เปลี่ยนรหัสผ่าน: รหัสปัจจุบันไม่ถูกต้อง")
            flash("รหัสผ่านปัจจุบันไม่ถูกต้อง", "danger")
            return render_template("auth/change_password.html", form=form)
        current_user.set_password(form.new_password.data)
        db.session.commit()
        audit.log("change_password", "user", current_user.id)
        flash("เปลี่ยนรหัสผ่านเรียบร้อยแล้ว ครั้งต่อไปให้เข้าระบบด้วยรหัสใหม่", "success")
        return redirect(_default_landing_url(current_user))
    return render_template("auth/change_password.html", form=form)
