# แผนฟีเจอร์: ระบบดึงข่าวจาก RSS มาสรุปรายวัน (เฉพาะ 17 จังหวัดภาคเหนือ/เหนือตอนล่าง)

## 1. เป้าหมาย
สร้างระบบที่ทำงานอัตโนมัติทุกวัน โดย:
1. ดึงข่าวจากแหล่ง RSS ที่กำหนด
2. กรองเฉพาะข่าวที่เกี่ยวข้องกับ 17 จังหวัดเป้าหมาย
3. สรุปข่าวแบบง่าย (ไม่ใช้ AI — ใช้ title/description จาก RSS โดยตรง, ตัดคำ/ลบ HTML tags)
4. เผยแพร่ผลลัพธ์เป็นเว็บเพจ (static site) และแจ้งเตือนผ่าน Line/Email
5. รันอัตโนมัติทุกวันด้วย GitHub Actions (cron)

## 2. จังหวัดเป้าหมาย (17 จังหวัด)
เชียงใหม่, เชียงราย, ลำพูน, ลำปาง, พะเยา, แพร่, น่าน, แม่ฮ่องสอน, ตาก,
สุโขทัย, อุตรดิตถ์, กำแพงเพชร, พิษณุโลก, พิจิตร, เพชรบูรณ์, นครสวรรค์, อุทัยธานี

เก็บเป็นค่าคงที่ในไฟล์ config (`config/provinces.yaml`) พร้อมคำพ้อง/ชื่อเรียกอื่น
(เช่น "เชียงใหม่" อาจปรากฏใน RSS เป็น "จ.เชียงใหม่", "Chiang Mai") เพื่อให้ตัวกรองแม่นยำขึ้น

## 3. สแตกเทคโนโลยี
- Python 3.11+
- `feedparser` — parse RSS/Atom feeds
- `PyYAML` — โหลด config (feeds, provinces)
- `Jinja2` — render static HTML
- `requests` — ส่ง Line Notify / เรียก webhook
- `smtplib` (built-in) — ส่งอีเมล
- SQLite (built-in `sqlite3`) — เก็บ id ข่าวที่เคยประมวลผลแล้ว (กันข่าวซ้ำ)

## 4. โครงสร้างโปรเจกต์ (แผน)
```
News_Report/
├── config/
│   ├── feeds.yaml            # รายการ RSS feed URL + หมวดหมู่
│   └── provinces.yaml        # 17 จังหวัด + คำพ้อง
├── news_report/
│   ├── __init__.py
│   ├── fetcher.py            # ดึง+parse RSS ทุก feed
│   ├── province_filter.py    # กรองข่าวที่พาดพิงจังหวัดเป้าหมาย
│   ├── summarizer.py         # สรุปแบบง่าย (strip HTML, ตัดความยาว)
│   ├── storage.py            # SQLite กันข่าวซ้ำ + เก็บประวัติรายวัน
│   ├── site_generator.py     # render static HTML (Jinja2) -> docs/site
│   ├── notifier.py           # ส่ง Line Notify / Email
│   └── main.py               # orchestrator: fetch -> filter -> summarize -> เก็บ -> เว็บ -> แจ้งเตือน
├── templates/
│   ├── index.html            # หน้ารวมรายงานล่าสุด/ย้อนหลัง
│   └── daily.html            # หน้ารายงานของแต่ละวัน (แยกตามจังหวัด)
├── docs/site/                # ผลลัพธ์ static site (สำหรับ GitHub Pages)
├── data/
│   └── seen.db                # SQLite เก็บ id ข่าวที่ประมวลผลแล้ว
├── .github/workflows/
│   └── daily-report.yml      # cron รันทุกวัน
├── tests/
│   ├── test_fetcher.py
│   ├── test_province_filter.py
│   └── test_summarizer.py
├── requirements.txt
└── README.md
```

## 5. Pipeline การทำงานรายวัน (`main.py`)
1. โหลด `feeds.yaml` และ `provinces.yaml`
2. ดึงข่าวทุก feed ด้วย `feedparser` → ได้ list ของ (title, link, summary, published, source)
3. ข้ามข่าวที่เคยเห็นแล้ว (เช็คจาก `link`/`guid` ใน SQLite)
4. ใช้ `province_filter.py` ตรวจ title+summary ว่ามีชื่อจังหวัด (หรือคำพ้อง) ใน 17 จังหวัดหรือไม่
   - เก็บ tag จังหวัดที่ match ไว้กับข่าวนั้น (ข่าวหนึ่งอาจ match หลายจังหวัด)
5. ข่าวที่ผ่านตัวกรอง → `summarizer.py` ทำความสะอาด HTML และตัดสรุปให้สั้นลง (เช่น 200 ตัวอักษรแรกของ description)
6. บันทึกผลลัพธ์ของวันนั้นเป็น JSON (`data/reports/YYYY-MM-DD.json`) จัดกลุ่มตามจังหวัด
7. `site_generator.py` render หน้า HTML ใหม่จาก JSON ทั้งหมด (รายวัน + หน้ารวม) ไปที่ `docs/site/`
8. `notifier.py` ส่งสรุปย่อ (จำนวนข่าวใหม่ + ลิงก์ไปหน้าเว็บ) ผ่าน Line Notify และ/หรือ Email
9. บันทึก id ข่าวที่ประมวลผลแล้วลง SQLite กันซ้ำในรอบถัดไป

## 6. การเผยแพร่ผลลัพธ์
- **Static site**: render เป็น HTML ใน `docs/site/` แล้วเปิดใช้ GitHub Pages (source: `docs/`)
  หน้าเว็บแสดงข่าวแยกตามจังหวัด + วันที่ ย้อนหลังได้
- **Line Notify**: POST ไปยัง Line Notify API พร้อมข้อความสรุป (ต้องใช้ `LINE_NOTIFY_TOKEN` เก็บใน GitHub Secrets)
- **Email**: ส่งผ่าน SMTP (ต้องใช้ `SMTP_HOST/USER/PASS` เก็บใน GitHub Secrets)

## 7. การตั้งเวลาอัตโนมัติ
- ใช้ GitHub Actions: `.github/workflows/daily-report.yml`
- `schedule: cron: "0 23 * * *"` (23:00 UTC = 06:00 เวลาไทย) — รันสรุปข่าวของ "เมื่อวาน-ถึงตอนเช้านี้"
- ขั้นตอนใน workflow: checkout → setup python → pip install -r requirements.txt → รัน `python -m news_report.main`
  → commit ผลลัพธ์ (`docs/site/`, `data/`) กลับเข้า repo → push

## 8. แผนการทดสอบ
- `test_fetcher.py`: mock RSS response, ตรวจว่า parse ได้ครบ field
- `test_province_filter.py`: ตรวจว่าข่าวที่มี/ไม่มีชื่อจังหวัด (รวมคำพ้อง) ถูกกรองถูกต้อง, ข่าวไม่เกี่ยวข้องกับ 17 จังหวัดถูกตัดออก
- `test_summarizer.py`: ตรวจว่าลบ HTML tag และตัดความยาวได้ถูกต้อง
- ทดสอบ end-to-end ด้วย feed ตัวอย่างจริง 2-3 แหล่งก่อน deploy จริง

## 9. Milestones
1. **Phase 1 — Core pipeline**: fetcher + province_filter + summarizer + storage (ทดสอบ local, print ผลลัพธ์)
2. **Phase 2 — Static site**: site_generator + templates + ตั้งค่า GitHub Pages
3. **Phase 3 — Notifications**: Line Notify + Email
4. **Phase 4 — Automation**: GitHub Actions workflow + secrets + ทดสอบรันจริงตามตาราง
5. **Phase 5 — เก็บรายละเอียด**: ปรับแต่งรายชื่อ feed, ปรับ threshold การกรอง, ปรับ template ตามฟีดแบ็ก

## 10. สิ่งที่ต้องตัดสินใจเพิ่มเติมจากผู้ใช้ (ก่อนเริ่ม implement)
- รายชื่อ RSS feed ที่ต้องการดึง (เช่น สำนักข่าวไทยไหนบ้าง — ไทยรัฐ, เดลินิวส์, สำนักข่าวท้องถิ่นภาคเหนือ ฯลฯ)
- ต้องการ Line Notify, Email, หรือทั้งสองอย่าง (ถ้าทั้งสอง ต้องเตรียม credential ทั้งคู่)
- ความถี่/เวลาที่ต้องการให้รันแต่ละวัน (ค่าเริ่มต้นที่เสนอ: 06:00 เวลาไทย)
