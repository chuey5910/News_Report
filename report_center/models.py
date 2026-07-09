from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(128), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(16), nullable=False, default="user")  # "admin" | "user"
    is_approved = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    login_logs = db.relationship("LoginLog", backref="user", lazy="dynamic")

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_admin(self):
        return self.role == "admin"

    # Flask-Login: block sign-in for accounts pending admin approval
    @property
    def is_active(self):
        return self.is_approved


class LoginLog(db.Model):
    __tablename__ = "login_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    username_attempted = db.Column(db.String(64), nullable=False)
    success = db.Column(db.Boolean, nullable=False)
    reason = db.Column(db.String(128), nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)


class ReportMixin:
    """Common columns shared by all four report categories."""

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


RELIABILITY_LEVELS = ["สูง", "ปานกลาง", "ต่ำ"]
PRIORITY_LEVELS = ["ด่วนที่สุด", "ด่วนมาก", "ด่วน", "ปกติ"]


class AdvanceNews(db.Model, ReportMixin):
    """ข่าวล่วงหน้า — intelligence / advance-warning news."""

    __tablename__ = "advance_news"

    event_datetime = db.Column(db.DateTime, nullable=True)  # คาดว่าจะเกิดเหตุเมื่อใด
    location = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    target_group = db.Column(db.String(255), nullable=True)  # กลุ่มเป้าหมาย/บุคคลที่เกี่ยวข้อง
    source = db.Column(db.String(255), nullable=True)  # แหล่งข่าว
    reliability_level = db.Column(db.String(16), nullable=False, default="ปานกลาง")
    priority_level = db.Column(db.String(16), nullable=False, default="ปกติ")
    preventive_measures = db.Column(db.Text, nullable=True)  # แนวทางเฝ้าระวัง/มาตรการรองรับ
    related_agency = db.Column(db.String(255), nullable=True)

    created_by = db.relationship("User", foreign_keys="AdvanceNews.created_by_id")


class NewsClosure(db.Model, ReportMixin):
    """ปิดข่าว — closing / resolution report, optionally linked to an AdvanceNews record."""

    __tablename__ = "news_closures"

    related_advance_id = db.Column(db.Integer, db.ForeignKey("advance_news.id"), nullable=True)
    reference_note = db.Column(db.String(255), nullable=True)  # อ้างอิงข่าวต้นเรื่อง ถ้าไม่ได้ผูก record
    closure_date = db.Column(db.DateTime, nullable=True)
    result_status = db.Column(db.String(32), nullable=False, default="ยังไม่ยืนยัน")
    operation_result = db.Column(db.Text, nullable=False)  # ผลการดำเนินการ
    responsible_person = db.Column(db.String(128), nullable=True)
    responsible_agency = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    created_by = db.relationship("User", foreign_keys="NewsClosure.created_by_id")
    related_advance = db.relationship("AdvanceNews", foreign_keys=[related_advance_id])


RESULT_STATUSES = ["จริง", "เท็จ", "ยังไม่ยืนยัน", "ระงับเหตุได้แล้ว", "คลี่คลายแล้ว"]


class SituationReport(db.Model, ReportMixin):
    """รายงานสถานการณ์ข่าว — ongoing situation report."""

    __tablename__ = "situation_reports"

    incident_datetime = db.Column(db.DateTime, nullable=True)
    location = db.Column(db.String(255), nullable=False)
    situation_type = db.Column(db.String(128), nullable=True)  # ประเภทสถานการณ์
    description = db.Column(db.Text, nullable=False)
    severity_level = db.Column(db.String(16), nullable=False, default="ปกติ")
    impact = db.Column(db.Text, nullable=True)  # ผลกระทบ
    initial_action = db.Column(db.Text, nullable=True)  # การดำเนินการเบื้องต้น
    related_agency = db.Column(db.String(255), nullable=True)
    current_status = db.Column(db.String(32), nullable=False, default="กำลังดำเนินการ")

    created_by = db.relationship("User", foreign_keys="SituationReport.created_by_id")


SITUATION_STATUSES = ["กำลังดำเนินการ", "ควบคุมได้แล้ว", "คลี่คลายแล้ว"]


class GeneralNews(db.Model, ReportMixin):
    """ข่าวทั่วไป — general news log."""

    __tablename__ = "general_news"

    news_date = db.Column(db.DateTime, nullable=True)
    source = db.Column(db.String(255), nullable=True)
    summary = db.Column(db.Text, nullable=False)
    area = db.Column(db.String(255), nullable=True)  # พื้นที่/จังหวัดที่เกี่ยวข้อง
    category_tag = db.Column(db.String(128), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    created_by = db.relationship("User", foreign_keys="GeneralNews.created_by_id")


# Registry used by views/templates to iterate over the 4 report categories generically.
REPORT_CATEGORIES = {
    "advance": {"model": AdvanceNews, "label": "ข่าวล่วงหน้า", "endpoint": "reports.advance"},
    "closure": {"model": NewsClosure, "label": "ปิดข่าว", "endpoint": "reports.closure"},
    "situation": {"model": SituationReport, "label": "รายงานสถานการณ์ข่าว", "endpoint": "reports.situation"},
    "general": {"model": GeneralNews, "label": "ข่าวทั่วไป", "endpoint": "reports.general"},
}
