from flask_wtf import FlaskForm
from wtforms import (
    DateTimeField,
    PasswordField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, Optional, EqualTo, Regexp

from .models import (
    PRIORITY_LEVELS,
    RELIABILITY_LEVELS,
    RESULT_STATUSES,
    SITUATION_STATUSES,
)


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
    title = StringField("หัวข้อข่าว", validators=[DataRequired(), Length(max=255)])
    event_datetime = DateTimeField(
        "วัน/เวลา ที่คาดว่าจะเกิดเหตุ", format="%Y-%m-%dT%H:%M", validators=[Optional()]
    )
    location = StringField("สถานที่", validators=[DataRequired(), Length(max=255)])
    description = TextAreaField("รายละเอียดเหตุการณ์ที่คาดว่าจะเกิด", validators=[DataRequired()])
    target_group = StringField("กลุ่มเป้าหมาย/บุคคลที่เกี่ยวข้อง", validators=[Optional(), Length(max=255)])
    source = StringField("แหล่งข่าว", validators=[Optional(), Length(max=255)])
    reliability_level = SelectField("ระดับความน่าเชื่อถือของข่าว", choices=_choices(RELIABILITY_LEVELS))
    priority_level = SelectField("ระดับความสำคัญ", choices=_choices(PRIORITY_LEVELS))
    preventive_measures = TextAreaField("แนวทางเฝ้าระวัง/มาตรการรองรับ", validators=[Optional()])
    related_agency = StringField("หน่วยงานที่เกี่ยวข้อง", validators=[Optional(), Length(max=255)])


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
