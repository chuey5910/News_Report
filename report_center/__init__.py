import os
from datetime import timedelta

import click
from flask import Flask

from .config import Config  # importing this also loads .env (see config._load_dotenv)
from .extensions import db, login_manager


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    os.makedirs(os.path.join(app.root_path, "instance"), exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from . import models  # noqa: F401  (ensure models are registered before create_all)

    @login_manager.user_loader
    def load_user(user_id):
        return models.User.query.get(int(user_id))

    # เวลาในระบบเก็บเป็น UTC — แสดงผลเป็นเวลาไทย (UTC+7) และปีเป็น พ.ศ. ทุกจุดผ่าน filter นี้
    @app.template_filter("thai_time")
    def thai_time(dt, fmt="%d/%m/%Y %H:%M"):
        if dt is None:
            return "-"
        local = dt + timedelta(hours=7)
        return local.strftime(fmt.replace("%Y", str(local.year + 543)))

    # วัน-เวลากิจกรรมเก็บเป็นเวลาไทยอยู่แล้ว (ไม่เลื่อนโซนเวลา) — แสดงปีเป็น พ.ศ.
    @app.template_filter("be_date")
    def be_date(dt, fmt="%d/%m/%Y"):
        if dt is None:
            return "-"
        return dt.strftime(fmt.replace("%Y", str(dt.year + 543)))

    # เมนูซ้าย (แท็บบันทึกข่าว 3 แบบฟอร์ม) ใช้ใน base.html ทุกหน้า
    @app.context_processor
    def inject_form_tabs():
        return {
            "report_form_tabs": models.REPORT_FORM_TABS,
            "report_type_labels": models.REPORT_TYPE_LABELS,
        }

    from .auth import bp as auth_bp
    from .reports import bp as reports_bp
    from .admin import bp as admin_bp
    from .api import bp as api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    from flask import redirect, url_for
    from flask_login import current_user

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            if current_user.is_admin:
                return redirect(url_for("reports.dashboard"))
            return redirect(url_for("reports.new_report", form_type="advance"))
        return redirect(url_for("auth.login"))

    with app.app_context():
        db.create_all()
        _auto_migrate()

    register_cli(app)

    return app


def _auto_migrate():
    """อัปเกรดฐานข้อมูลเดิมอัตโนมัติตอนสตาร์ท (SQLite ADD COLUMN — ไม่กระทบข้อมูลเดิม).

    create_all() สร้างเฉพาะ "ตารางใหม่" แต่ไม่เพิ่มคอลัมน์ให้ตารางที่มีอยู่แล้ว
    ส่วนนี้จึงตรวจและเติมคอลัมน์ที่ขาดให้ ทำให้เครื่องจริงอัปเดตได้ด้วย git pull + restart
    """
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    new_columns = {
        "news_reports": [
            ("activity_detail", "TEXT"),
            ("considerations", "TEXT"),
            ("mass_members", "VARCHAR(255)"),
            ("mass_media", "VARCHAR(255)"),
            ("mass_others", "VARCHAR(255)"),
            ("due_alert_sent_at", "DATETIME"),
        ],
        "news_report_leaders": [("position", "VARCHAR(128)"), ("role", "VARCHAR(255)")],
        "news_report_vehicles": [("owner", "VARCHAR(128)"), ("usage", "VARCHAR(255)")],
    }
    with db.engine.begin() as conn:
        for table, columns in new_columns.items():
            existing = {col["name"] for col in inspector.get_columns(table)}
            for name, ddl_type in columns:
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl_type}"))
        # แบบฟอร์ม "เหตุการณ์(สถานการณ์)" กับ "ข่าวทั่วไป" ถูกรวมเป็นแท็บเดียว
        # จึงรวมข้อมูลเก่าประเภท general เข้ากับ incident
        conn.execute(text("UPDATE news_reports SET report_type = 'incident' WHERE report_type = 'general'"))
        # ซ่อมวันที่กิจกรรมที่ถูกกรอกเป็นปี พ.ศ. (เช่น 2569) ให้เป็น ค.ศ. (-543 ปี)
        for column in ("event_datetime", "event_end_datetime"):
            conn.execute(
                text(
                    f"UPDATE news_reports SET {column} = datetime({column}, '-543 years') "
                    f"WHERE {column} IS NOT NULL "
                    f"AND CAST(strftime('%Y', {column}) AS INTEGER) >= 2400"
                )
            )


def register_cli(app):
    @app.cli.command("create-admin")
    @click.argument("username")
    @click.argument("full_name")
    @click.password_option()
    def create_admin(username, full_name, password):
        """Create (or promote) an approved admin user, e.g.:
        flask --app report_center create-admin admin "ผู้ดูแลระบบ"
        """
        from .models import User

        user = User.query.filter_by(username=username).first()
        if user is None:
            user = User(username=username, full_name=full_name, role="admin", is_approved=True)
        else:
            user.full_name = full_name
            user.role = "admin"
            user.is_approved = True
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Admin user '{username}' created/updated and approved.")

    @app.cli.command("line-daily")
    def line_daily():
        """ส่งสรุป "กิจกรรมวันนี้ + ล่วงหน้า 7 วัน" เข้า LINE OA — ตั้ง cron เรียกทุกเช้า เช่น
        0 7 * * * cd /path/to/News_Report && .venv/bin/flask --app report_center line-daily
        (เวลาบนเครื่องเป็นเวลาไทยอยู่แล้ว จึงใช้ 7 โมงเช้าตรงๆ ได้)
        """
        from . import line_notify
        from .reports import thai_today, todays_advance_items, upcoming_advance_items

        if not line_notify.is_configured(app.config):
            click.echo("LINE ยังไม่ได้ตั้งค่า (LINE_CHANNEL_ACCESS_TOKEN) — ข้าม")
            return
        today = thai_today()
        today_items = todays_advance_items(today)
        upcoming_items = upcoming_advance_items(today)
        # ส่งทุกเช้าเสมอ แม้ไม่มีกิจกรรม — เพื่อยืนยันว่าระบบแจ้งเตือนยังทำงานอยู่
        ok = line_notify.push_text(
            app, line_notify.daily_message(app.config, today_items, upcoming_items, today)
        )
        click.echo(
            f"ส่งสรุป วันนี้ {len(today_items)} + ล่วงหน้า {len(upcoming_items)} กิจกรรม: "
            f"{'สำเร็จ' if ok else 'ไม่สำเร็จ (ดู log)'}"
        )

    @app.cli.command("line-status")
    def line_status():
        """ตรวจสถานะการแจ้งเตือน LINE: โหมดส่ง (broadcast/เข้ากลุ่ม) + โควตาข้อความเดือนนี้."""
        from . import line_notify

        if not line_notify.is_configured(app.config):
            click.echo("LINE ยังไม่ได้ตั้งค่า (LINE_CHANNEL_ACCESS_TOKEN)")
            return

        targets = [t.strip() for t in (app.config.get("LINE_TARGET_IDS") or "").split(",") if t.strip()]
        if targets:
            kinds = ["กลุ่ม" if t.startswith("C") else "รายบุคคล" for t in targets]
            click.echo(f"โหมดส่ง: push เข้าเป้าหมาย {len(targets)} รายการ ({', '.join(kinds)}) — นับโควตา 1 ข้อความ/เป้าหมาย/ครั้ง")
        else:
            click.echo("โหมดส่ง: BROADCAST หาทุกคนที่เป็นเพื่อน OA — นับโควตาคูณจำนวนเพื่อนทุกครั้ง ⚠️")

        try:
            status = line_notify.get_status(app.config)
        except Exception as exc:
            click.echo(f"เรียกดูโควตาจาก LINE ไม่สำเร็จ: {exc}")
            return
        if status["limit"] is None:
            click.echo(f"โควตา: ไม่จำกัด | ใช้ไปเดือนนี้ {status['used']} ข้อความ")
        else:
            remaining = status["limit"] - status["used"]
            click.echo(f"โควตาเดือนนี้: ใช้ไป {status['used']} / {status['limit']} ข้อความ (เหลือ {remaining})")
            if remaining <= 0:
                click.echo("⚠️ โควตาหมดแล้ว — LINE จะปฏิเสธทุกข้อความ (429) จนกว่าจะรีเซ็ตวันที่ 1 ของเดือนหน้า หรืออัปเกรดแพ็กเกจ")

    @app.cli.command("line-due")
    def line_due():
        """แจ้งเตือน LINE ล่วงหน้าก่อนถึงกำหนดเวลาทำกิจกรรม (ค่าเริ่มต้น 20 นาที —
        ปรับได้ด้วย env LINE_DUE_LEAD_MINUTES) — ตั้ง cron เรียกทุก 5 นาที เช่น
        */5 * * * * cd /path/to/News_Report && .venv/bin/flask --app report_center line-due
        ส่งครั้งเดียวต่อกิจกรรม (กันซ้ำด้วย due_alert_sent_at)
        """
        from datetime import datetime as dt, timedelta as td

        from sqlalchemy import text as sql_text

        from . import line_notify
        from .models import NewsReport

        if not line_notify.is_configured(app.config):
            click.echo("LINE ยังไม่ได้ตั้งค่า (LINE_CHANNEL_ACCESS_TOKEN) — ข้าม")
            return

        thai_now = dt.utcnow() + td(hours=7)
        lead = td(minutes=app.config["LINE_DUE_LEAD_MINUTES"])
        # แจ้งเมื่อ (เวลากิจกรรม - lead) มาถึงแล้ว; ย้อนหลังไม่เกิน 2 ชม.
        # กันไม่ให้ไปไล่แจ้งกิจกรรมเก่าๆ หลังระบบหยุดไปนาน
        items = (
            NewsReport.query.filter(
                NewsReport.report_type == "advance",
                NewsReport.event_datetime <= thai_now + lead,
                NewsReport.event_datetime > thai_now + lead - td(hours=2),
                NewsReport.due_alert_sent_at.is_(None),
            )
            .order_by(NewsReport.event_datetime.asc())
            .all()
        )
        sent = 0
        for item in items:
            if line_notify.push_text(app, line_notify.due_message(app.config, item, thai_now)):
                # อัปเดตตรงๆ ด้วย SQL เพื่อไม่ให้ไปกระตุ้น updated_at (ไม่ใช่การแก้ไขข้อมูล)
                db.session.execute(
                    sql_text("UPDATE news_reports SET due_alert_sent_at = :now WHERE id = :id"),
                    {"now": dt.utcnow(), "id": item.id},
                )
                sent += 1
        db.session.commit()
        click.echo(f"แจ้งเตือนถึงเวลากิจกรรม {sent}/{len(items)} รายการ")

    @app.cli.command("sync-sheets")
    def sync_sheets():
        """Backfill: push ALL existing reports into the configured Google Sheet.
        Useful after first setting up Google Sheets credentials.
        """
        from . import sheets_sync
        from .models import NewsReport

        if not sheets_sync.is_configured(app.config):
            click.echo("Google Sheets ยังไม่ได้ตั้งค่า (GOOGLE_SHEETS_SPREADSHEET_ID) — ข้ามการ sync")
            return

        reports = NewsReport.query.order_by(NewsReport.id.asc()).all()
        ok = sheets_sync.sync_all(app, reports)
        click.echo(f"Synced {ok}/{len(reports)} reports to Google Sheets.")
