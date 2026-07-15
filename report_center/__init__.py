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

    # เวลาในระบบเก็บเป็น UTC — แสดงผลเป็นเวลาไทย (UTC+7) ทุกจุดผ่าน filter นี้
    @app.template_filter("thai_time")
    def thai_time(dt, fmt="%d/%m/%Y %H:%M"):
        if dt is None:
            return "-"
        return (dt + timedelta(hours=7)).strftime(fmt)

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
