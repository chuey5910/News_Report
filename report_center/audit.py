"""บันทึกการใช้งาน (audit) — เรียก audit.log(...) จากจุดที่มีการกระทำสำคัญ

ไม่มีทางทำให้งานหลักล้ม: ถ้าบันทึกไม่ได้จะ log error แล้วไปต่อ
"""

import logging

from flask import has_request_context, request
from flask_login import current_user

from .extensions import db
from .models import AuditLog

logger = logging.getLogger(__name__)

# ชื่อการกระทำ → คำไทยสำหรับหน้าแสดงผล
ACTION_LABELS = {
    "login": "เข้าสู่ระบบ",
    "logout": "ออกจากระบบ",
    "auto_logout": "ออกจากระบบอัตโนมัติ",
    "view_report": "เปิดดูรายงาน",
    "view_shared": "เปิดดูจากลิงก์การ์ด",
    "create_report": "บันทึกรายงาน",
    "edit_report": "แก้ไขรายงาน",
    "resubmit_report": "แก้ไขแล้วส่งใหม่",
    "delete_report": "ลบรายงาน",
    "verify_report": "ยืนยันรายงาน",
    "return_report": "ส่งกลับให้แก้ไข",
    "send_line_card": "ส่งการ์ดไลน์",
    "approve_user": "อนุมัติผู้ใช้",
    "revoke_user": "ระงับผู้ใช้",
    "update_user": "เปลี่ยนสังกัด/ตำแหน่ง",
    "reset_password": "ตั้งรหัสผ่านใหม่ให้ผู้ใช้",
    "change_password": "เปลี่ยนรหัสผ่านตัวเอง",
    "register": "สมัครสมาชิก",
}


def client_ip():
    if not has_request_context():
        return None
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or None


def log(action, target_type=None, target_id=None, detail=None, user=None, commit=True):
    """บันทึก 1 รายการ — user ว่าง = ใช้คนที่ล็อกอินอยู่ (ถ้ามี)."""
    try:
        if user is None and has_request_context() and current_user.is_authenticated:
            user = current_user
        entry = AuditLog(
            user_id=user.id if user else None,
            username=user.username if user else None,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=(detail or "")[:512] or None,
            ip_address=client_ip(),
        )
        db.session.add(entry)
        if commit:
            db.session.commit()
    except Exception as exc:  # ห้ามให้ audit ทำงานหลักพัง
        logger.error("บันทึก audit ไม่สำเร็จ (%s): %s", action, exc)
        db.session.rollback()
