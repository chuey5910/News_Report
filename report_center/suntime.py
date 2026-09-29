"""คำนวณเวลาพระอาทิตย์ขึ้น-ตก เพื่อสลับธีมสว่าง/มืดให้เองตามเวลาจริง

ใช้สูตรดาราศาสตร์ (NOAA solar calculator) คำนวณในเครื่อง ไม่ต้องเรียก API ภายนอก
คลาดเคลื่อนไม่เกิน 1-2 นาที ซึ่งเพียงพอกับการสลับสีหน้าเว็บ
"""

import math
from datetime import datetime, timedelta

# จุดอ้างอิง: เชียงใหม่ (กลางพื้นที่รับผิดชอบ 17 จังหวัดภาคเหนือ)
REF_LAT = 18.7883
REF_LNG = 98.9853
THAI_OFFSET_HOURS = 7


def _sun_event_hour(day, latitude, longitude, sunrise):
    """คืนเวลา (ชั่วโมงทศนิยม ตามเวลาไทย) ของพระอาทิตย์ขึ้นหรือตกในวันนั้น

    คืน None เมื่อวันนั้นดวงอาทิตย์ไม่ขึ้น/ไม่ตกเลย (เกิดได้เฉพาะแถบขั้วโลก)
    """
    n = day.timetuple().tm_yday
    lng_hour = longitude / 15.0
    t = n + ((6 if sunrise else 18) - lng_hour) / 24.0

    mean_anomaly = 0.9856 * t - 3.289
    true_lng = (
        mean_anomaly
        + 1.916 * math.sin(math.radians(mean_anomaly))
        + 0.020 * math.sin(math.radians(2 * mean_anomaly))
        + 282.634
    ) % 360

    right_asc = math.degrees(math.atan(0.91764 * math.tan(math.radians(true_lng)))) % 360
    # ย้าย right ascension ให้อยู่ควอดแรนต์เดียวกับ true longitude
    right_asc += (true_lng // 90) * 90 - (right_asc // 90) * 90
    right_asc /= 15.0

    sin_dec = 0.39782 * math.sin(math.radians(true_lng))
    cos_dec = math.cos(math.asin(sin_dec))

    # -0.833° = ขอบบนดวงอาทิตย์แตะเส้นขอบฟ้า (รวมการหักเหของบรรยากาศ)
    cos_h = (
        math.cos(math.radians(90.833)) - sin_dec * math.sin(math.radians(latitude))
    ) / (cos_dec * math.cos(math.radians(latitude)))
    if not -1 <= cos_h <= 1:
        return None

    h = math.degrees(math.acos(cos_h))
    if sunrise:
        h = 360 - h
    h /= 15.0

    mean_time = h + right_asc - 0.06571 * t - 6.622
    return (mean_time - lng_hour + THAI_OFFSET_HOURS) % 24


def theme_for_now(latitude=REF_LAT, longitude=REF_LNG, now_thai=None):
    """คืน ("light"|"dark", นาทีที่เหลือก่อนเปลี่ยนธีมครั้งถัดไป) ตามเวลาไทยปัจจุบัน."""
    if now_thai is None:
        now_thai = datetime.utcnow() + timedelta(hours=THAI_OFFSET_HOURS)

    sunrise = _sun_event_hour(now_thai.date(), latitude, longitude, sunrise=True)
    sunset = _sun_event_hour(now_thai.date(), latitude, longitude, sunrise=False)
    if sunrise is None or sunset is None:  # กลางวัน/กลางคืนตลอดวัน — ใช้สว่างไว้ก่อน
        return "light", 60

    hour_now = now_thai.hour + now_thai.minute / 60 + now_thai.second / 3600
    if sunrise <= hour_now < sunset:
        return "light", max(1, round((sunset - hour_now) * 60))
    # กลางคืน: ถ้ายังไม่ถึงรุ่งเช้าให้รอถึงพระอาทิตย์ขึ้นวันนี้ ถ้าเลยค่ำแล้วให้รอของวันพรุ่งนี้
    if hour_now < sunrise:
        minutes_left = (sunrise - hour_now) * 60
    else:
        next_sunrise = _sun_event_hour(
            now_thai.date() + timedelta(days=1), latitude, longitude, sunrise=True
        )
        minutes_left = ((next_sunrise or sunrise) + 24 - hour_now) * 60
    return "dark", max(1, round(minutes_left))
