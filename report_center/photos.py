"""รูปภาพแนบรายงาน — รับไฟล์จากฟอร์ม ย่อขนาด เก็บลงดิสก์ และลบเมื่อรายงานถูกลบ

- เก็บที่ UPLOAD_DIR/<เลขรายงาน>/<ชื่อสุ่ม>.jpg (รูปใหญ่ ด้านยาวสุด 1600px) และ _t.jpg (รูปย่อ 480px)
- รูปจากมือถือ 3–5 MB จะเหลือราว 200–400 KB ประหยัดพื้นที่ NAS และโหลดเร็ว
- จำกัด MAX_PHOTOS รูปต่อรายงาน ใส่ไม่ครบได้ ไม่บังคับคำบรรยาย
- ไฟล์ที่ไม่ใช่รูป หรือเปิดไม่ขึ้น จะถูกข้ามพร้อมแจ้งผู้ใช้ ไม่ทำให้การบันทึกล้ม
"""

import io
import os
import shutil
import uuid

from flask import current_app

from .extensions import db
from .models import NewsReportPhoto

MAX_PHOTOS = 10
MAX_SIDE = 1600          # ด้านยาวสุดของรูปใหญ่ (พิกเซล)
THUMB_SIDE = 480         # ด้านยาวสุดของรูปย่อ
JPEG_QUALITY = 82


def upload_dir(config=None):
    return (config or current_app.config)["UPLOAD_DIR"]


def report_dir(report_id, config=None):
    return os.path.join(upload_dir(config), str(report_id))


def photo_path(photo, thumb=False, config=None):
    name = photo.thumb_filename if thumb else photo.filename
    return os.path.join(report_dir(photo.news_report_id, config), name)


def process_image(data):
    """ย่อรูปเป็น JPEG 2 ขนาด — คืน (รูปใหญ่ bytes, รูปย่อ bytes, กว้าง, สูง) หรือ raise ถ้าไม่ใช่รูป."""
    from PIL import Image, ImageOps

    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)      # รูปจากมือถือมักเก็บทิศทางไว้ใน EXIF ต้องหมุนให้ถูกก่อน
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    big = img.copy()
    big.thumbnail((MAX_SIDE, MAX_SIDE))
    big_buf = io.BytesIO()
    big.save(big_buf, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)

    small = img.copy()
    small.thumbnail((THUMB_SIDE, THUMB_SIDE))
    small_buf = io.BytesIO()
    small.save(small_buf, "JPEG", quality=78, optimize=True)
    return big_buf.getvalue(), small_buf.getvalue(), big.width, big.height


def save_uploads(item, files, captions):
    """เก็บรูปที่อัปโหลดมาให้รายงาน item — คืน (จำนวนที่เก็บได้, รายการข้อความเตือน)."""
    warnings = []
    room = MAX_PHOTOS - len(item.photos)
    incoming = [f for f in files if f and f.filename]
    if len(incoming) > room:
        warnings.append(f"แนบรูปได้สูงสุด {MAX_PHOTOS} รูปต่อรายงาน — เก็บให้ {max(room, 0)} รูปแรก ที่เหลือไม่ได้บันทึก")
        incoming = incoming[:max(room, 0)]

    saved = 0
    target_dir = report_dir(item.id)
    for index, storage in enumerate(incoming):
        data = storage.read()
        try:
            big, small, width, height = process_image(data)
        except Exception:  # ไฟล์ไม่ใช่รูป/เสียหาย — ข้ามไฟล์นี้
            warnings.append(f"ไฟล์ “{storage.filename}” ไม่ใช่รูปภาพที่เปิดได้ — ข้าม")
            continue
        os.makedirs(target_dir, exist_ok=True)
        name = f"{uuid.uuid4().hex}.jpg"
        with open(os.path.join(target_dir, name), "wb") as fh:
            fh.write(big)
        with open(os.path.join(target_dir, name[:-4] + "_t.jpg"), "wb") as fh:
            fh.write(small)
        caption = (captions[index] if index < len(captions) else "").strip()[:255] or None
        item.photos.append(
            NewsReportPhoto(filename=name, caption=caption, width=width, height=height, size_bytes=len(big))
        )
        saved += 1
    if saved:
        db.session.commit()
    return saved, warnings


def apply_edits(item, delete_ids, captions_by_id):
    """หน้าแก้ไข: ลบรูปที่ติ๊ก และอัปเดตคำบรรยายของรูปเดิม."""
    delete_ids = {int(x) for x in delete_ids if str(x).isdigit()}
    changed = False
    for photo in list(item.photos):
        if photo.id in delete_ids:
            remove_files(photo)
            item.photos.remove(photo)
            changed = True
            continue
        if photo.id in captions_by_id:
            new_caption = (captions_by_id[photo.id] or "").strip()[:255] or None
            if new_caption != photo.caption:
                photo.caption = new_caption
                changed = True
    if changed:
        db.session.commit()


def remove_files(photo):
    for path in (photo_path(photo), photo_path(photo, thumb=True)):
        try:
            os.remove(path)
        except OSError:
            pass


def remove_report_dir(report_id, config=None):
    """ลบโฟลเดอร์รูปทั้งหมดของรายงาน (เรียกตอนลบรายงาน)."""
    shutil.rmtree(report_dir(report_id, config), ignore_errors=True)


def mirror_to(backup_root, config=None):
    """คัดลอกรูปที่ยังไม่มีในโฟลเดอร์สำรอง (ใช้กับ backup-db) — คืนจำนวนไฟล์ที่คัดลอกเพิ่ม."""
    src_root = upload_dir(config)
    if not os.path.isdir(src_root):
        return 0
    copied = 0
    for folder, _dirs, files in os.walk(src_root):
        rel = os.path.relpath(folder, src_root)
        dest_folder = os.path.join(backup_root, rel) if rel != "." else backup_root
        for name in files:
            dest = os.path.join(dest_folder, name)
            if not os.path.exists(dest):
                os.makedirs(dest_folder, exist_ok=True)
                shutil.copy2(os.path.join(folder, name), dest)
                copied += 1
    return copied
