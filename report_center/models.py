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
        # ระบุ pbkdf2:sha256 ตรงๆ แทนค่า default (scrypt) เพราะ Python ที่ติดมากับ
        # macOS บางรุ่นคอมไพล์โดยไม่มี hashlib.scrypt ทำให้ล็อกอิน/สร้างผู้ใช้พัง
        self.password_hash = generate_password_hash(raw_password, method="pbkdf2:sha256")

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


PERMIT_STATUSES = ["มีการขออนุญาต", "ไม่มีการขออนุญาต"]
YES_NO = ["มี", "ไม่มี"]

ACTIVITY_TYPES = [
    "ร้องเรียน",
    "เสวนา",
    "แสดงออกเชิงสัญลักษณ์ในพื้นที่",
    "ประชุมสมาชิก/รวบรวมกลุ่มจัดกิจกรรม",
    "หน่วยงาน/สส.ลงพื้นที่",
]

PROBLEM_GROUP_TYPES = [
    "ความมั่นคงด้านสถาบันพระมหากษัตริย์",
    "กลุ่มการเมือง",
    "กลุ่มเศรษฐกิจ",
    "กลุ่มด้านสิ่งแวดล้อม",
    "กลุ่มผู้ได้รับผลกระทบจากโครงการของรัฐ",
    "กลุ่มด้านสังคมและสิทธิมนุษยชน",
    "ยาเสพติด",
    "ด้านต่างประเทศ (ด้านอาชญากรรมข้ามชาติก่อการร้ายสากล)",
]

# ประเภทรายงาน — กำหนดโดย "แท็บฟอร์ม" ที่ผู้ใช้เลือกจากเมนูซ้าย (ไม่มีช่องเลือกในฟอร์มแล้ว)
# เหตุการณ์(สถานการณ์) กับข่าวทั่วไปถูกรวมเป็นแบบฟอร์มเดียว จึงเก็บเป็นประเภทเดียว ("incident")
REPORT_TYPE_CHOICES = [
    ("advance", "ข่าวล่วงหน้า"),
    ("closure", "ปิดข่าว"),
    ("incident", "รายงานเหตุการณ์/ข่าวทั่วไป"),
]
REPORT_TYPE_LABELS = dict(REPORT_TYPE_CHOICES)

# ชื่อแท็บในเมนูซ้าย (บันทึกข่าว) — ทั้ง 3 แท็บใช้ template ฟอร์มเดียวกัน
# แต่โชว์/ซ่อนบางส่วนต่างกันตามประเภท
REPORT_FORM_TABS = [
    ("advance", "แบบรายงานข่าวล่วงหน้า"),
    ("closure", "แบบรายงานปิดข่าว"),
    ("incident", "แบบรายงานเหตุการณ์(สถานการณ์)/ข่าวทั่วไป"),
]

# ความเกี่ยวข้องกับบุคคล/องค์กรอื่นๆ (ฟอร์มข่าวล่วงหน้า) — 3 ลักษณะความเกี่ยวข้อง
AFFILIATE_CATEGORIES = ["เป็นเครือข่ายของกลุ่ม", "ได้รับการประสานมาจาก", "เคยร่วมกิจกรรมด้วยกับ"]

# กลุ่มการเมือง องค์กร หรือบุคคลอื่นๆ ที่มาเกี่ยวข้อง (ฟอร์มปิดข่าว) — 3 กลุ่ม
RELATED_ORG_CATEGORIES = ["พรรคการเมือง", "NGO", "หน่วยงานรัฐ"]

# สันติบาล จว. — เลือกได้จังหวัดเดียวต่อรายงาน (radio) เก็บเป็น string เดียว
SPECIAL_BRANCH_PROVINCES = [
    "ลำพูน", "พิจิตร", "น่าน", "เชียงราย", "พิษณุโลก", "อุทัยธานี",
    "เพชรบูรณ์", "สุโขทัย", "อุตรดิตถ์", "แพร่", "พะเยา", "นครสวรรค์",
    "กำแพงเพชร", "ลำปาง", "ตาก", "แม่ฮ่องสอน", "เชียงใหม่",
]

# พิกัดศาลากลาง/ตัวเมืองของแต่ละจังหวัด — ใช้ปักหมุดบนแผนที่เมื่อรายงานไม่ได้ระบุพิกัดเอง
# (ระดับจังหวัด ไม่ใช่จุดเกิดเหตุจริง — ถ้าต้องการตำแหน่งแม่น ให้จิ้มพิกัดในฟอร์ม)
PROVINCE_COORDS = {
    "เชียงใหม่": (18.7883, 98.9853),
    "เชียงราย": (19.9105, 99.8406),
    "ลำพูน": (18.5744, 99.0087),
    "ลำปาง": (18.2888, 99.4908),
    "แม่ฮ่องสอน": (19.3020, 97.9654),
    "น่าน": (18.7756, 100.7730),
    "พะเยา": (19.1664, 99.9003),
    "แพร่": (18.1445, 100.1405),
    "อุตรดิตถ์": (17.6200, 100.0993),
    "สุโขทัย": (17.0056, 99.8265),
    "ตาก": (16.8839, 99.1258),
    "พิษณุโลก": (16.8211, 100.2659),
    "พิจิตร": (16.4429, 100.3487),
    "เพชรบูรณ์": (16.4190, 101.1591),
    "กำแพงเพชร": (16.4828, 99.5220),
    "นครสวรรค์": (15.7047, 100.1372),
    "อุทัยธานี": (15.3835, 100.0245),
}

# ระดับสถานการณ์ — กำหนดสีหมุดบนแผนที่ (แดงกับเหลืองสงวนไว้ 2 ระดับนี้เท่านั้น)
SITUATION_LEVELS = ["ปกติ", "เฝ้าระวัง", "มีผลกระทบ"]
SITUATION_COLORS = {
    "ปกติ": "#16a34a",      # เขียว
    "เฝ้าระวัง": "#eab308",  # เหลือง
    "มีผลกระทบ": "#dc2626",  # แดง
}
SITUATION_DEFAULT = "ปกติ"


class NewsReport(db.Model):
    """รายงานข่าว — the single unified report form (ชื่อกิจกรรม = title)."""

    __tablename__ = "news_reports"

    id = db.Column(db.Integer, primary_key=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # เลขที่อ้างอิง รันต่อกันทั้งระบบภายในปี พ.ศ. เดียวกัน เช่น "2569/0004"
    ref_number = db.Column(db.String(16), unique=True, index=True, nullable=True)
    # เวลาที่ส่งการ์ดรายงานนี้เข้ากลุ่มไลน์ครั้งล่าสุด (ว่าง = ยังไม่เคยส่ง)
    line_card_sent_at = db.Column(db.DateTime, nullable=True)

    # ประเภทรายงาน (เลือกได้ข้อเดียว — advance | closure | incident | general)
    report_type = db.Column(db.String(16), nullable=False)

    # สันติบาล จว. (เลือกได้จังหวัดเดียว)
    special_branch_province = db.Column(db.String(32), nullable=True)

    title = db.Column(db.String(255), nullable=False)  # ชื่อกิจกรรม

    activity_types = db.Column(db.Text, nullable=True)  # ประเภทกิจกรรม (comma-separated, multi-select)
    problem_group_types = db.Column(db.Text, nullable=True)  # ประเภทกลุ่มปัญหา (comma-separated, multi-select)

    event_datetime = db.Column(db.DateTime, nullable=True)  # เริ่มกิจกรรม (วันที่ + เวลา รวมกัน)
    event_end_datetime = db.Column(db.DateTime, nullable=True)  # สิ้นสุดกิจกรรม (วันที่ + เวลา รวมกัน)
    due_alert_sent_at = db.Column(db.DateTime, nullable=True)  # ส่งแจ้งเตือน LINE "ถึงเวลากิจกรรม" ไปแล้วเมื่อ (กันส่งซ้ำ)

    permit_status = db.Column(db.String(32), nullable=False, default="ไม่มีการขออนุญาต")
    permit_location = db.Column(db.String(255), nullable=True)  # ขออนุญาตที่ไหน (ถ้ามีการขออนุญาต)
    permit_duration_days = db.Column(db.Integer, nullable=True)  # ระยะเวลาทำกิจกรรม (วัน)

    location = db.Column(db.String(255), nullable=False)  # สถานที่นัดหมาย
    # พิกัดที่ผู้กรอกจิ้มบนแผนที่ (ไม่บังคับ) — ถ้าเว้นว่างจะปักหมุดที่ตัวเมืองของจังหวัดให้
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    situation_level = db.Column(db.String(16), nullable=True)  # ปกติ | เฝ้าระวัง | มีผลกระทบ
    group_name = db.Column(db.String(255), nullable=True)  # ชื่อกลุ่ม

    mass_count = db.Column(db.String(64), nullable=True)  # จำนวนมวลชน (ที่มาร่วมงานจริง)
    mass_members = db.Column(db.String(255), nullable=True)  # จำแนก: สมาชิกกลุ่มอะไร จำนวนเท่าไร
    mass_media = db.Column(db.String(255), nullable=True)  # จำแนก: นักข่าว/สื่อ จำนวนเท่าไร
    mass_others = db.Column(db.String(255), nullable=True)  # จำแนก: อื่นๆ จำนวนเท่าไร
    activity_format = db.Column(db.Text, nullable=True)  # รูปแบบการจัดกิจกรรม
    demands = db.Column(db.Text, nullable=False)  # ข้อเรียกร้อง/วัตถุประสงค์
    activity_detail = db.Column(db.Text, nullable=True)  # รายละเอียดการทำกิจกรรม (ไทม์ไลน์/เนื้อหาเสวนา)
    supporters = db.Column(db.Text, nullable=True)  # ผู้สนับสนุน (ข้อความอิสระ — ฟอร์มข่าวล่วงหน้า/เหตุการณ์)
    affiliations = db.Column(db.Text, nullable=True)  # ความเชื่อมโยงกับบุคคล/องค์กรอื่นๆ

    overnight_equipment_status = db.Column(db.String(16), nullable=False, default="ไม่มี")  # สัมภาระค้างแรม/อุปกรณ์
    overnight_equipment_detail = db.Column(db.Text, nullable=True)

    vehicle_status = db.Column(db.String(16), nullable=False, default="ไม่มี")  # ยานพาหนะ

    other_info = db.Column(db.Text, nullable=True)  # ข้อมูลน่าสนใจอื่นๆ
    trend_assessment = db.Column(db.Text, nullable=True)  # แนวโน้มสถานการณ์ / แนวโน้มในอนาคต
    considerations = db.Column(db.Text, nullable=True)  # ข้อพิจารณา (แยกจากแนวโน้ม)
    reporter_name = db.Column(db.String(128), nullable=True)  # ผู้รายงาน
    reporter_phone = db.Column(db.String(32), nullable=True)  # เบอร์ติดต่อ

    created_by = db.relationship("User", foreign_keys=[created_by_id])
    leaders = db.relationship(
        "NewsReportLeader", backref="news_report", cascade="all, delete-orphan", order_by="NewsReportLeader.id"
    )
    vehicles = db.relationship(
        "NewsReportVehicle", backref="news_report", cascade="all, delete-orphan", order_by="NewsReportVehicle.id"
    )
    people = db.relationship(
        "NewsReportPerson", backref="news_report", cascade="all, delete-orphan", order_by="NewsReportPerson.id"
    )
    media_posts = db.relationship(
        "NewsReportMedia", backref="news_report", cascade="all, delete-orphan", order_by="NewsReportMedia.id"
    )
    photos = db.relationship(
        "NewsReportPhoto", backref="news_report", cascade="all, delete-orphan", order_by="NewsReportPhoto.id"
    )

    def people_of(self, kind, category=None):
        return [
            p for p in self.people
            if p.kind == kind and (category is None or p.category == category)
        ]


class NewsReportLeader(db.Model):
    """แกนนำ (รายการเพิ่มได้ตามจำนวนที่เลือก) — ตำแหน่ง/บทบาทใช้ในฟอร์มปิดข่าว."""

    __tablename__ = "news_report_leaders"

    id = db.Column(db.Integer, primary_key=True)
    news_report_id = db.Column(db.Integer, db.ForeignKey("news_reports.id"), nullable=False)
    full_name = db.Column(db.String(128), nullable=False)
    position = db.Column(db.String(128), nullable=True)  # ตำแหน่ง
    role = db.Column(db.String(255), nullable=True)  # บทบาทหน้าที่


class NewsReportVehicle(db.Model):
    """ยานพาหนะ (รายการเพิ่มได้ตามจำนวนที่เลือก) — เจ้าของ/การใช้งานใช้ในฟอร์มปิดข่าว."""

    __tablename__ = "news_report_vehicles"

    id = db.Column(db.Integer, primary_key=True)
    news_report_id = db.Column(db.Integer, db.ForeignKey("news_reports.id"), nullable=False)
    vehicle_type = db.Column(db.String(128), nullable=True)  # ประเภทรถยนต์
    plate_number = db.Column(db.String(32), nullable=True)  # หมายเลขทะเบียน
    province = db.Column(db.String(64), nullable=True)  # จังหวัด
    color = db.Column(db.String(64), nullable=True)  # สี
    owner = db.Column(db.String(128), nullable=True)  # เจ้าของ/ผู้ครอบครอง
    usage = db.Column(db.String(255), nullable=True)  # ใช้ทำอะไรในกิจกรรม


class NewsReportPerson(db.Model):
    """บุคคล/องค์กรที่เกี่ยวข้องกับรายงาน (โครงสร้างเดียวรองรับหลายหมวด):

    kind = "affiliate"    ความเกี่ยวข้องกับบุคคล/องค์กรอื่นๆ (ข่าวล่วงหน้า, category = ลักษณะความเกี่ยวข้อง)
    kind = "participant"  แนวร่วมหรือบุคคลสำคัญที่มาร่วมกิจกรรม (ปิดข่าว)
    kind = "supporter"    ผู้สนับสนุน/ผู้อยู่เบื้องหลัง (ปิดข่าว)
    kind = "related_org"  กลุ่มการเมือง องค์กร บุคคลอื่นๆ ที่มาเกี่ยวข้อง (ปิดข่าว, category = พรรคการเมือง/NGO/หน่วยงานรัฐ)
    """

    __tablename__ = "news_report_people"

    id = db.Column(db.Integer, primary_key=True)
    news_report_id = db.Column(db.Integer, db.ForeignKey("news_reports.id"), nullable=False)
    kind = db.Column(db.String(32), nullable=False, index=True)
    category = db.Column(db.String(64), nullable=True)
    full_name = db.Column(db.String(128), nullable=False)
    group_name = db.Column(db.String(255), nullable=True)  # กลุ่ม / กลุ่ม-ตำแหน่ง
    role = db.Column(db.String(255), nullable=True)  # บทบาท/หน้าที่


class NewsReportMedia(db.Model):
    """การเผยแพร่กิจกรรมทางสื่อออนไลน์และกระแสสนใจ (ปิดข่าว)."""

    __tablename__ = "news_report_media"

    id = db.Column(db.Integer, primary_key=True)
    news_report_id = db.Column(db.Integer, db.ForeignKey("news_reports.id"), nullable=False)
    page_name = db.Column(db.String(255), nullable=False)  # ชื่อเพจ
    likes = db.Column(db.String(64), nullable=True)  # ยอดคนกด Like
    shares = db.Column(db.String(64), nullable=True)  # ยอดคนกดแชร์


class NewsReportPhoto(db.Model):
    """รูปภาพแนบรายงาน — ไฟล์จริงอยู่ในโฟลเดอร์ uploads/<เลขรายงาน>/ (ดู photos.py) ตารางนี้เก็บแค่ชื่อไฟล์กับคำบรรยาย."""

    __tablename__ = "news_report_photos"

    id = db.Column(db.Integer, primary_key=True)
    news_report_id = db.Column(db.Integer, db.ForeignKey("news_reports.id"), nullable=False, index=True)
    filename = db.Column(db.String(64), nullable=False)      # ชื่อไฟล์ที่ระบบตั้งเอง (สุ่ม) ลงท้าย .jpg
    caption = db.Column(db.String(255), nullable=True)       # คำบรรยายใต้รูป (ไม่บังคับ)
    width = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)
    size_bytes = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @property
    def thumb_filename(self):
        return self.filename[:-4] + "_t.jpg"
