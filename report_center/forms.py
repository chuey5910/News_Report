from flask_wtf import FlaskForm
from wtforms import (
    DateTimeField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional, EqualTo, Regexp

from .models import (
    PERMIT_STATUSES,
    PRIORITY_LEVELS,
    RESULT_STATUSES,
    SITUATION_STATUSES,
    YES_NO,
)

LEADER_COUNT_CHOICES = [(i, str(i)) for i in range(0, 21)]
VEHICLE_COUNT_CHOICES = [(i, str(i)) for i in range(0, 11)]


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


def _choices(values):
    return [(v, v) for v in values]


class AdvanceNewsForm(FlaskForm):
    title = StringField("ชื่อกิจกรรม", validators=[DataRequired(), Length(max=255)])
    event_datetime = DateTimeField("วันเวลานัดหมายทำกิจกรรม", format="%Y-%m-%dT%H:%M", validators=[Optional()])
    permit_status = SelectField("การขออนุญาต", choices=_choices(PERMIT_STATUSES))
    permit_location = StringField("ขออนุญาตที่ไหน", validators=[Optional(), Length(max=255)])
    permit_duration_days = IntegerField(
        "ระยะเวลาทำกิจกรรม (วัน)", validators=[Optional(), NumberRange(min=0, max=3650)]
    )

    location = StringField("สถานที่นัดหมาย", validators=[DataRequired(), Length(max=255)])
    group_name = StringField("ชื่อกลุ่ม", validators=[Optional(), Length(max=255)])

    leader_count = SelectField("จำนวนแกนนำ (คน)", choices=LEADER_COUNT_CHOICES, coerce=int, default=0)

    mass_count = StringField("จำนวนมวลชน", validators=[Optional(), Length(max=64)])
    activity_format = TextAreaField("รูปแบบการจัดกิจกรรม", validators=[Optional()])
    demands = TextAreaField("ข้อเรียกร้อง/วัตถุประสงค์", validators=[DataRequired()])
    supporters = TextAreaField("ผู้สนับสนุน", validators=[Optional()])
    affiliations = TextAreaField("ความเชื่อมโยงกับบุคคลหรือองค์กรอื่นๆ", validators=[Optional()])

    overnight_equipment_status = SelectField("สัมภาระค้างแรม/อุปกรณ์", choices=_choices(YES_NO))
    overnight_equipment_detail = TextAreaField("รายละเอียดสัมภาระ/อุปกรณ์", validators=[Optional()])

    vehicle_status = SelectField("ยานพาหนะ", choices=_choices(YES_NO))
    vehicle_count = SelectField("จำนวนยานพาหนะ (คัน)", choices=VEHICLE_COUNT_CHOICES, coerce=int, default=0)

    other_info = TextAreaField("ข้อมูลน่าสนใจอื่นๆ", validators=[Optional()])
    trend_assessment = TextAreaField("แนวโน้ม/ข้อพิจารณา", validators=[Optional()])
    reporter_name = StringField("ผู้รายงาน", validators=[Optional(), Length(max=128)])
    reporter_phone = StringField("เบอร์ติดต่อ", validators=[Optional(), Length(max=32)])


class NewsClosureForm(FlaskForm):
    title = StringField("หัวข้อข่าว", validators=[DataRequired(), Length(max=255)])
    related_advance_id = SelectField("ผูกกับข่าวล่วงหน้า (ถ้ามี)", coerce=int, validators=[Optional()])
    reference_note = StringField("อ้างอิงข่าวต้นเรื่อง (ถ้าไม่ได้ผูกรายการด้านบน)", validators=[Optional(), Length(max=255)])
    closure_date = DateTimeField("วันที่ปิดข่าว", format="%Y-%m-%dT%H:%M", validators=[Optional()])
    result_status = SelectField("สถานะผลการตรวจสอบ", choices=_choices(RESULT_STATUSES))
    operation_result = TextAreaField("ผลการดำเนินการ", validators=[DataRequired()])
    responsible_person = StringField("ผู้รับผิดชอบ", validators=[Optional(), Length(max=128)])
    responsible_agency = StringField("หน่วยงานที่ดำเนินการ", validators=[Optional(), Length(max=255)])
    notes = TextAreaField("หมายเหตุ", validators=[Optional()])


class SituationReportForm(FlaskForm):
    title = StringField("หัวข้อรายงาน", validators=[DataRequired(), Length(max=255)])
    incident_datetime = DateTimeField("วัน/เวลาที่เกิดเหตุ", format="%Y-%m-%dT%H:%M", validators=[Optional()])
    location = StringField("สถานที่เกิดเหตุ", validators=[DataRequired(), Length(max=255)])
    situation_type = StringField("ประเภทสถานการณ์", validators=[Optional(), Length(max=128)])
    description = TextAreaField("รายละเอียดสถานการณ์", validators=[DataRequired()])
    severity_level = SelectField("ระดับความสำคัญ", choices=_choices(PRIORITY_LEVELS))
    impact = TextAreaField("ผลกระทบ", validators=[Optional()])
    initial_action = TextAreaField("การดำเนินการเบื้องต้น", validators=[Optional()])
    related_agency = StringField("หน่วยงานที่เกี่ยวข้อง", validators=[Optional(), Length(max=255)])
    current_status = SelectField("สถานะปัจจุบัน", choices=_choices(SITUATION_STATUSES))


class GeneralNewsForm(FlaskForm):
    title = StringField("หัวข้อข่าว", validators=[DataRequired(), Length(max=255)])
    news_date = DateTimeField("วันที่ข่าว", format="%Y-%m-%dT%H:%M", validators=[Optional()])
    source = StringField("แหล่งที่มา", validators=[Optional(), Length(max=255)])
    summary = TextAreaField("เนื้อหาข่าวโดยสรุป", validators=[DataRequired()])
    area = StringField("พื้นที่/จังหวัดที่เกี่ยวข้อง", validators=[Optional(), Length(max=255)])
    category_tag = StringField("หมวดหมู่", validators=[Optional(), Length(max=128)])
    notes = TextAreaField("หมายเหตุ", validators=[Optional()])
