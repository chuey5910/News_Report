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


PERMIT_STATUSES = ["มีการขออนุญาต", "ไม่มีการขออนุญาต"]
YES_NO = ["มี", "ไม่มี"]


class ActivityFieldsMixin:
    """Shared activity-report columns used by both ข่าวล่วงหน้า and ปิดข่าว
    (ปิดข่าว uses the exact same form/fields as ข่าวล่วงหน้า)."""

    event_datetime = db.Column(db.DateTime, nullable=True)  # เริ่มกิจกรรม (วันที่ + เวลา รวมกัน)
    event_end_datetime = db.Column(db.DateTime, nullable=True)  # สิ้นสุดกิจกรรม (วันที่ + เวลา รวมกัน)

    permit_status = db.Column(db.String(32), nullable=False, default="ไม่มีการขออนุญาต")
    permit_location = db.Column(db.String(255), nullable=True)  # ขออนุญาตที่ไหน (ถ้ามีการขออนุญาต)
    permit_duration_days = db.Column(db.Integer, nullable=True)  # ระยะเวลาทำกิจกรรม (วัน)

    location = db.Column(db.String(255), nullable=False)  # สถานที่นัดหมาย
    group_name = db.Column(db.String(255), nullable=True)  # ชื่อกลุ่ม

    mass_count = db.Column(db.String(64), nullable=True)  # จำนวนมวลชน
    activity_format = db.Column(db.Text, nullable=True)  # รูปแบบการจัดกิจกรรม
    demands = db.Column(db.Text, nullable=False)  # ข้อเรียกร้อง/วัตถุประสงค์
    supporters = db.Column(db.Text, nullable=True)  # ผู้สนับสนุน
    affiliations = db.Column(db.Text, nullable=True)  # ความเชื่อมโยงกับบุคคล/องค์กรอื่นๆ

    overnight_equipment_status = db.Column(db.String(16), nullable=False, default="ไม่มี")  # สัมภาระค้างแรม/อุปกรณ์
    overnight_equipment_detail = db.Column(db.Text, nullable=True)

    vehicle_status = db.Column(db.String(16), nullable=False, default="ไม่มี")  # ยานพาหนะ

    other_info = db.Column(db.Text, nullable=True)  # ข้อมูลน่าสนใจอื่นๆ
    trend_assessment = db.Column(db.Text, nullable=True)  # แนวโน้ม/ข้อพิจารณา
    reporter_name = db.Column(db.String(128), nullable=True)  # ผู้รายงาน
    reporter_phone = db.Column(db.String(32), nullable=True)  # เบอร์ติดต่อ


class AdvanceNews(db.Model, ReportMixin, ActivityFieldsMixin):
    """ข่าวล่วงหน้า — advance notice of a planned activity/gathering (title = ชื่อกิจกรรม)."""

    __tablename__ = "advance_news"

    created_by = db.relationship("User", foreign_keys="AdvanceNews.created_by_id")
    leaders = db.relationship(
        "AdvanceNewsLeader", backref="advance_news", cascade="all, delete-orphan", order_by="AdvanceNewsLeader.id"
    )
    vehicles = db.relationship(
        "AdvanceNewsVehicle", backref="advance_news", cascade="all, delete-orphan", order_by="AdvanceNewsVehicle.id"
    )


class AdvanceNewsLeader(db.Model):
    """ชื่อ-นามสกุล แกนนำ (รายการเพิ่มได้ตามจำนวนที่เลือก)."""

    __tablename__ = "advance_news_leaders"

    id = db.Column(db.Integer, primary_key=True)
    advance_news_id = db.Column(db.Integer, db.ForeignKey("advance_news.id"), nullable=False)
    full_name = db.Column(db.String(128), nullable=False)


class AdvanceNewsVehicle(db.Model):
    """ยานพาหนะ (รายการเพิ่มได้ตามจำนวนที่เลือก)."""

    __tablename__ = "advance_news_vehicles"

    id = db.Column(db.Integer, primary_key=True)
    advance_news_id = db.Column(db.Integer, db.ForeignKey("advance_news.id"), nullable=False)
    vehicle_type = db.Column(db.String(128), nullable=True)  # ประเภทรถยนต์
    plate_number = db.Column(db.String(32), nullable=True)  # หมายเลขทะเบียน
    province = db.Column(db.String(64), nullable=True)  # จังหวัด
    color = db.Column(db.String(64), nullable=True)  # สี


class NewsClosure(db.Model, ReportMixin, ActivityFieldsMixin):
    """ปิดข่าว — ใช้ฟอร์ม/ฟิลด์ชุดเดียวกันกับข่าวล่วงหน้าทุกประการ เพิ่มเติมคือผูกกับ
    ข่าวล่วงหน้าต้นเรื่องได้ (ถ้ามี)."""

    __tablename__ = "news_closures"

    related_advance_id = db.Column(db.Integer, db.ForeignKey("advance_news.id"), nullable=True)

    created_by = db.relationship("User", foreign_keys="NewsClosure.created_by_id")
    related_advance = db.relationship("AdvanceNews", foreign_keys=[related_advance_id])
    leaders = db.relationship(
        "NewsClosureLeader", backref="news_closure", cascade="all, delete-orphan", order_by="NewsClosureLeader.id"
    )
    vehicles = db.relationship(
        "NewsClosureVehicle", backref="news_closure", cascade="all, delete-orphan", order_by="NewsClosureVehicle.id"
    )


class NewsClosureLeader(db.Model):
    __tablename__ = "news_closure_leaders"

    id = db.Column(db.Integer, primary_key=True)
    news_closure_id = db.Column(db.Integer, db.ForeignKey("news_closures.id"), nullable=False)
    full_name = db.Column(db.String(128), nullable=False)


class NewsClosureVehicle(db.Model):
    __tablename__ = "news_closure_vehicles"

    id = db.Column(db.Integer, primary_key=True)
    news_closure_id = db.Column(db.Integer, db.ForeignKey("news_closures.id"), nullable=False)
    vehicle_type = db.Column(db.String(128), nullable=True)
    plate_number = db.Column(db.String(32), nullable=True)
    province = db.Column(db.String(64), nullable=True)
    color = db.Column(db.String(64), nullable=True)


class FiveWOneHMixin:
    """หัวข้อ 5W1H ใช้ร่วมกันระหว่างรายงานสถานการณ์ข่าวและข่าวทั่วไป."""

    who = db.Column(db.Text, nullable=True)  # ใคร
    what = db.Column(db.Text, nullable=False)  # เกิดอะไรขึ้น
    when = db.Column(db.DateTime, nullable=True)  # เมื่อไหร่
    where = db.Column(db.String(255), nullable=True)  # ที่ไหน
    why = db.Column(db.Text, nullable=True)  # ทำไม/เพราะเหตุใด
    how = db.Column(db.Text, nullable=True)  # อย่างไร


class SituationReport(db.Model, ReportMixin, FiveWOneHMixin):
    """รายงานสถานการณ์ข่าว — ใช้หัวข้อ 5W1H."""

    __tablename__ = "situation_reports"

    created_by = db.relationship("User", foreign_keys="SituationReport.created_by_id")


class GeneralNews(db.Model, ReportMixin, FiveWOneHMixin):
    """ข่าวทั่วไป — ใช้หัวข้อ 5W1H."""

    __tablename__ = "general_news"

    created_by = db.relationship("User", foreign_keys="GeneralNews.created_by_id")


# Registry used by views/templates to iterate over the 4 report categories generically.
REPORT_CATEGORIES = {
    "advance": {"model": AdvanceNews, "label": "ข่าวล่วงหน้า", "endpoint": "reports.advance"},
    "closure": {"model": NewsClosure, "label": "ปิดข่าว", "endpoint": "reports.closure"},
    "situation": {"model": SituationReport, "label": "รายงานสถานการณ์ข่าว", "endpoint": "reports.situation"},
    "general": {"model": GeneralNews, "label": "ข่าวทั่วไป", "endpoint": "reports.general"},
}
