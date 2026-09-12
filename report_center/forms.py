from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    IntegerField,
    PasswordField,
    RadioField,
    SelectField,
    SelectMultipleField,
    StringField,
    TextAreaField,
    TimeField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional, EqualTo, Regexp
from wtforms.widgets import CheckboxInput, ListWidget

from .models import (
    ACTIVITY_TYPES,
    PERMIT_STATUSES,
    PROBLEM_GROUP_TYPES,
    SPECIAL_BRANCH_PROVINCES,
    YES_NO,
)

LEADER_COUNT_CHOICES = [(i, str(i)) for i in range(0, 21)]
VEHICLE_COUNT_CHOICES = [(i, str(i)) for i in range(0, 11)]
PEOPLE_COUNT_CHOICES = [(i, str(i)) for i in range(0, 21)]
SMALL_COUNT_CHOICES = [(i, str(i)) for i in range(0, 11)]

ACTIVITY_DETAIL_PLACEHOLDER = (
    "เวลา....น.........................\n"
    "เวลา.....น. เสร็จกิจกรรม\n"
    "(กรณีมีการเสวนา ปราศรัย ให้ใส่รายละเอียด ชื่อสกุล เนื้อหาพอสังเขปที่บุคคลนั้นๆ ได้มีการพูดถึงด้วย)"
)

CLOSURE_TREND_PLACEHOLDER = (
    "(จะมีการเคลื่อนไหวต่อหรือไม่อย่างไร ฯ จะขยายตัวหรือไม่ จะเป็นอย่างไรต่อ "
    "จะยุติบทบาท/หมดปัญหาไม่เคลื่อนไหว)"
)


class MultiCheckboxField(SelectMultipleField):
    """Renders as a group of checkboxes instead of a <select multiple>."""

    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class RegisterForm(FlaskForm):
    username = StringField(
        "ชื่อผู้ใช้",
        validators=[
            DataRequired(message="กรุณากรอกชื่อผู้ใช้"),
            Length(min=4, max=64),
            Regexp(r"^[A-Za-z0-9_.]+$", message="ใช้ได้เฉพาะตัวอักษร a-z, ตัวเลข, . และ _"),
        ],
    )
    full_name = StringField("ชื่อ-นามสกุล", validators=[DataRequired(), Length(max=128)])
    password = PasswordField("รหัสผ่าน", validators=[DataRequired(), Length(min=8, message="รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร")])
    confirm_password = PasswordField(
        "ยืนยันรหัสผ่าน", validators=[DataRequired(), EqualTo("password", message="รหัสผ่านไม่ตรงกัน")]
    )


class LoginForm(FlaskForm):
    username = StringField("ชื่อผู้ใช้", validators=[DataRequired()])
    password = PasswordField("รหัสผ่าน", validators=[DataRequired()])


class DeleteForm(FlaskForm):
    """ฟอร์มเปล่าสำหรับปุ่มลบ — มีไว้เพื่อ CSRF token เท่านั้น."""


def _choices(values):
    return [(v, v) for v in values]


class NewsReportForm(FlaskForm):
    """รายงานข่าว — template ฟอร์มเดียว ใช้ร่วมกัน 3 แท็บ (ข่าวล่วงหน้า/ปิดข่าว/เหตุการณ์-ข่าวทั่วไป)
    ประเภทรายงานถูกกำหนดจากแท็บที่เปิด ไม่ใช่ช่องในฟอร์ม"""

    special_branch_province = RadioField(
        "สันติบาล จว.", choices=_choices(SPECIAL_BRANCH_PROVINCES), validators=[Optional()]
    )

    title = StringField("ชื่อกิจกรรม", validators=[DataRequired(), Length(max=255)])

    activity_types = MultiCheckboxField("ประเภทกิจกรรม", choices=_choices(ACTIVITY_TYPES), validators=[Optional()])
    problem_group_types = MultiCheckboxField(
        "ประเภทกลุ่มปัญหา", choices=_choices(PROBLEM_GROUP_TYPES), validators=[Optional()]
    )

    event_date = DateField("วันที่นัดหมายทำกิจกรรม", validators=[Optional()])
    event_time = TimeField("เวลานัดหมาย", validators=[Optional()])
    event_end_date = DateField("วันที่สิ้นสุดกิจกรรม", validators=[Optional()])
    event_end_time = TimeField("เวลาสิ้นสุด", validators=[Optional()])

    permit_status = SelectField("การขออนุญาต", choices=_choices(PERMIT_STATUSES))
    permit_location = StringField("ขออนุญาตที่ไหน", validators=[Optional(), Length(max=255)])
    permit_duration_days = IntegerField(
        "ระยะเวลาทำกิจกรรม (วัน)", validators=[Optional(), NumberRange(min=0, max=3650)]
    )

    location = StringField("สถานที่นัดหมาย", validators=[DataRequired(), Length(max=255)])
    group_name = StringField("ชื่อกลุ่ม", validators=[Optional(), Length(max=255)])

    leader_count = SelectField("แกนนำ (คน)", choices=LEADER_COUNT_CHOICES, coerce=int, default=0)
    participant_count = SelectField(
        "แนวร่วมหรือบุคคลสำคัญที่มาร่วมกิจกรรม (คน)", choices=PEOPLE_COUNT_CHOICES, coerce=int, default=0
    )

    mass_count = StringField(
        "จำนวนมวลชน",
        validators=[Optional(), Length(max=64)],
        render_kw={"placeholder": "(มวลชนที่มาร่วมงานจริง)"},
    )
    mass_members = StringField("สมาชิกกลุ่มอะไร จำนวนเท่าไร", validators=[Optional(), Length(max=255)])
    mass_media = StringField("นักข่าว/สื่อ จำนวนเท่าไร", validators=[Optional(), Length(max=255)])
    mass_others = StringField("อื่นๆ จำนวนเท่าไร", validators=[Optional(), Length(max=255)])

    activity_format = TextAreaField("รูปแบบการจัดกิจกรรม", validators=[Optional()])
    demands = TextAreaField("ข้อเรียกร้อง/วัตถุประสงค์", validators=[DataRequired()])
    activity_detail = TextAreaField(
        "รายละเอียดการทำกิจกรรม",
        validators=[Optional()],
        render_kw={"placeholder": ACTIVITY_DETAIL_PLACEHOLDER, "class": "ta-tall"},
    )

    supporters = TextAreaField("ผู้สนับสนุน", validators=[Optional()])
    supporter_count = SelectField(
        "ผู้สนับสนุน/ผู้อยู่เบื้องหลัง (ถ้ามี) (คน)", choices=PEOPLE_COUNT_CHOICES, coerce=int, default=0
    )

    affiliations = TextAreaField("ความเชื่อมโยงกับบุคคลหรือองค์กรอื่นๆ", validators=[Optional()])
    aff_net_count = SelectField("เป็นเครือข่ายของกลุ่ม (จำนวน)", choices=SMALL_COUNT_CHOICES, coerce=int, default=0)
    aff_coord_count = SelectField("ได้รับการประสานมาจาก (จำนวน)", choices=SMALL_COUNT_CHOICES, coerce=int, default=0)
    aff_joint_count = SelectField("เคยร่วมกิจกรรมด้วยกับ (จำนวน)", choices=SMALL_COUNT_CHOICES, coerce=int, default=0)

    org_party_count = SelectField("พรรคการเมือง (จำนวน)", choices=SMALL_COUNT_CHOICES, coerce=int, default=0)
    org_ngo_count = SelectField("NGO (จำนวน)", choices=SMALL_COUNT_CHOICES, coerce=int, default=0)
    org_gov_count = SelectField("หน่วยงานรัฐ (จำนวน)", choices=SMALL_COUNT_CHOICES, coerce=int, default=0)

    media_count = SelectField(
        "การเผยแพร่กิจกรรมทางสื่อออนไลน์และกระแสสนใจ (ถ้ามี) (จำนวน)",
        choices=SMALL_COUNT_CHOICES, coerce=int, default=0,
    )

    overnight_equipment_status = SelectField("สัมภาระค้างแรม/อุปกรณ์", choices=_choices(YES_NO))
    overnight_equipment_detail = TextAreaField("รายละเอียดสัมภาระ/อุปกรณ์", validators=[Optional()])

    vehicle_status = SelectField("ยานพาหนะ", choices=_choices(YES_NO))
    vehicle_count = SelectField("จำนวนยานพาหนะ (คัน)", choices=VEHICLE_COUNT_CHOICES, coerce=int, default=0)

    other_info = TextAreaField("ข้อมูลน่าสนใจอื่นๆ", validators=[Optional()])
    trend_assessment = TextAreaField("แนวโน้มสถานการณ์", validators=[Optional()])
    considerations = TextAreaField("ข้อพิจารณา", validators=[Optional()])
    reporter_name = StringField("ผู้รายงาน", validators=[Optional(), Length(max=128)])
    reporter_phone = StringField("เบอร์ติดต่อ", validators=[Optional(), Length(max=32)])
