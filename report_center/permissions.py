"""กติกาสิทธิ์ของรายงาน — บังคับที่ server ทุกเส้นทาง (หน้าเว็บแค่ซ่อน/แสดงปุ่มตามนี้)

- ค้นหา/สถิติ/แผนที่/ไลน์/Sheets/API: เห็นเฉพาะรายงานที่ "ยืนยันแล้ว" — ทุกคนรวมแอดมิน
- รายงานที่ยังไม่ยืนยัน เปิดได้แค่ เจ้าของ, หัวหน้าสังกัดเดียวกับเจ้าของ, แอดมิน
- เจ้าหน้าที่แก้ได้เฉพาะงานตัวเองที่ยังไม่ยืนยัน; หัวหน้าแก้งานในสังกัดได้; แอดมินแก้ได้หมด
- ยืนยัน/ส่งกลับ: หัวหน้าสังกัดเดียวกับเจ้าของ หรือแอดมิน
"""

from .models import STATUS_VERIFIED, NewsReport


def verified_only(query):
    """กรองให้เหลือเฉพาะรายงานที่ยืนยันแล้ว — ใช้กับทุก query ที่ออกสู่สายตาคนทั่วไป."""
    return query.filter(NewsReport.status == STATUS_VERIFIED)


def can_view(user, report):
    if report.is_verified:
        return True
    return is_owner(user, report) or user.can_verify_unit(report.author_unit)


def is_owner(user, report):
    return report.created_by_id == user.id


def can_edit(user, report):
    if user.is_admin:
        return True
    if user.is_chief:
        return user.unit == report.author_unit or is_owner(user, report)
    return is_owner(user, report) and not report.is_verified


def can_verify(user, report):
    """ยืนยัน/ส่งกลับได้ไหม — เฉพาะรายงานที่ยังไม่ยืนยัน และผู้ใช้เป็นหัวหน้าสังกัดเจ้าของหรือแอดมิน."""
    if report.is_verified:
        return False
    return user.can_verify_unit(report.author_unit)


def can_delete(user, report):
    return user.is_admin
