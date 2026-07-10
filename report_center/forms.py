from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    DateTimeLocalField,
    IntegerField,
    PasswordField,
    SelectField,
    SelectMultipleField,
    StringField,
    TextAreaField,
    TimeField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional, EqualTo, Regexp
from wtforms.widgets import CheckboxInput, ListWidget

from .models import ACTIVITY_TYPES, PERMIT_STATUSES, PROBLEM_GROUP_TYPES, YES_NO

LEADER_COUNT_CHOICES = [(i, str(i)) for i in range(0, 21)]
VEHICLE_COUNT_CHOICES = [(i, str(i)) for i in range(0, 11)]


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


def _choices(values):
    return [(v, v) for v in values]


class ActivityReportForm(FlaskForm):
    """ฟิลด์ชุดเดียวกัน ใช้ทั้งข่าวล่วงหน้าและปิดข่าว."""

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


class AdvanceNewsForm(ActivityReportForm):
    """ข่าวล่วงหน้า."""


class NewsClosureForm(ActivityReportForm):
    """ปิดข่าว — ฟิลด์ชุดเดียวกันกับข่าวล่วงหน้า เพิ่มการผูกกับข่าวล่วงหน้าต้นเรื่อง (ถ้ามี)."""

    related_advance_id = SelectField("ผูกกับข่าวล่วงหน้า (ถ้ามี)", coerce=int, validators=[Optional()])


class FiveWOneHForm(FlaskForm):
    """หัวข้อ 5W1H ใช้ร่วมกันระหว่างรายงานสถานการณ์ข่าวและข่าวทั่วไป."""

    title = StringField("หัวข้อ", validators=[DataRequired(), Length(max=255)])
    who = TextAreaField("ใคร (Who)", validators=[Optional()])
    what = TextAreaField("เกิดอะไรขึ้น (What)", validators=[DataRequired()])
    when = DateTimeLocalField("เมื่อไหร่ (When)", validators=[Optional()])
    where = StringField("ที่ไหน (Where)", validators=[Optional(), Length(max=255)])
    why = TextAreaField("ทำไม/เพราะเหตุใด (Why)", validators=[Optional()])
    how = TextAreaField("อย่างไร (How)", validators=[Optional()])


class SituationReportForm(FiveWOneHForm):
    """รายงานสถานการณ์ข่าว."""


class GeneralNewsForm(FiveWOneHForm):
    """ข่าวทั่วไป."""
