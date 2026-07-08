# แผนฟีเจอร์: ระบบดึงข่าวจาก RSS มาสรุปรายวัน (เฉพาะ 17 จังหวัดภาคเหนือ/เหนือตอนล่าง)

## 1. เป้าหมาย
สร้างระบบที่ทำงานอัตโนมัติทุกวัน โดย:
1. ดึงข่าวจากแหล่ง RSS ทุกสำนักข่าว ทั้งไทยและต่างประเทศ
2. แปลข่าวต่างประเทศเป็นไทย (ใส่อ้างอิงแหล่งข่าวต้นฉบับเสมอ)
3. กรองเฉพาะข่าวที่เกี่ยวข้องกับ 17 จังหวัดเป้าหมาย
4. สรุปข่าวแบบง่าย (ไม่ใช้ AI — ใช้ title/description จาก RSS โดยตรง, ตัดคำ/ลบ HTML tags)
5. เผยแพร่ผลลัพธ์เป็นเว็บเพจ (static site) และแจ้งเตือนผ่าน **LINE OA**
6. รันอัตโนมัติทุกวัน เวลา **07:00 น.** ด้วย GitHub Actions (cron)

## 2. จังหวัดเป้าหมาย (17 จังหวัด)
เชียงใหม่, เชียงราย, ลำพูน, ลำปาง, พะเยา, แพร่, น่าน, แม่ฮ่องสอน, ตาก,
สุโขทัย, อุตรดิตถ์, กำแพงเพชร, พิษณุโลก, พิจิตร, เพชรบูรณ์, นครสวรรค์, อุทัยธานี

เก็บเป็นค่าคงที่ในไฟล์ config (`config/provinces.yaml`) พร้อมคำพ้อง/ชื่อเรียกอื่น ทั้งภาษาไทยและอังกฤษ
(เช่น "เชียงใหม่" อาจปรากฏใน RSS เป็น "จ.เชียงใหม่", "Chiang Mai") เพื่อให้ตัวกรองแม่นยำขึ้นและ
ใช้จับคู่ได้ทั้งกับข่าวไทยต้นฉบับและข่าวต่างประเทศที่แปลแล้ว

## 3. แหล่งข่าว (RSS Feeds)
- ครอบคลุม **ทุกสำนักข่าว** ทั้งสำนักข่าวไทย (ไทยรัฐ, เดลินิวส์, มติชน, ผู้จัดการ, สำนักข่าวไทย, ThaiPBS,
  สำนักข่าวท้องถิ่นภาคเหนือ ฯลฯ) และสำนักข่าวต่างประเทศ (BBC, Reuters, AP, Al Jazeera, CNA ฯลฯ)
- เก็บรายการ feed ทั้งหมดไว้ใน `config/feeds.yaml` โดยระบุ `language` (th/en/...) ต่อ feed
  เพื่อให้ pipeline รู้ว่า feed ไหนต้องแปล
- รายการเริ่มต้นจะเป็น feed สาธารณะที่ใช้งานได้จริง (ตรวจสอบ URL ใช้งานได้ก่อนใส่จริงในขั้น implement)
  และออกแบบให้เพิ่ม/ลด feed ได้ง่ายภายหลังโดยไม่ต้องแก้โค้ด

## 4. สแตกเทคโนโลยี
- Python 3.11+
- `feedparser` — parse RSS/Atom feeds
- `PyYAML` — โหลด config (feeds, provinces)
- `deep-translator` — แปลข่าวต่างประเทศเป็นไทย (ใช้ Google Translate แบบไม่ต้องขอ API key)
- `Jinja2` — render static HTML
- `requests` — เรียก LINE Messaging API
- SQLite (built-in `sqlite3`) — เก็บ id ข่าวที่เคยประมวลผลแล้ว (กันข่าวซ้ำ)

### หมายเหตุเรื่องการแปล
`deep-translator` ครอบ Google Translate แบบไม่เป็นทางการ ใช้ฟรีไม่ต้องมี API key แต่มีข้อจำกัด:
- อาจโดน rate-limit หรือบล็อกชั่วคราวถ้าเรียกถี่เกินไป → ออกแบบให้มี retry + delay ระหว่างการแปลแต่ละข่าว
- ไม่มี SLA รับประกันความเสถียร หากในอนาคตพบปัญหาใช้งานไม่ได้บ่อย ค่อยพิจารณาเปลี่ยนไปใช้ DeepL/Google Cloud
  Translation API (ต้องมี API key) ซึ่งออกแบบโค้ดให้สลับ provider ได้ง่าย (interface เดียวกัน)

### หมายเหตุเรื่อง LINE
LINE Notify (บริการเดิมที่ใช้ webhook ส่งข้อความง่ายๆ) **ถูกยกเลิกไปแล้วตั้งแต่ 31 มี.ค. 2025**
ดังนั้นระบบนี้จะใช้ **LINE Messaging API** ของ LINE Official Account (LINE OA) แทน:
- ส่งข้อความสรุปข่าวประจำวันด้วย **Broadcast Message API**
  (`POST https://api.line.me/v2/bot/message/broadcast`) ไปยังผู้ติดตาม LINE OA ทุกคน
- ต้องมี **Channel Access Token** ของ LINE OA (สร้างจาก LINE Developers Console) เก็บเป็น
  `LINE_CHANNEL_ACCESS_TOKEN` ใน GitHub Secrets
- ข้อความ broadcast มีข้อจำกัดความยาว/จำนวนข้อความต่อเดือนตาม LINE OA plan ของบัญชี — ถ้าข่าวเยอะ
  จะส่งเป็นสรุปย่อ (จำนวนข่าวใหม่ต่อจังหวัด) พร้อมลิงก์ไปหน้าเว็บฉบับเต็ม แทนการส่งเนื้อข่าวทั้งหมด

## 5. โครงสร้างโปรเจกต์ (แผน)
```
News_Report/
├── config/
│   ├── feeds.yaml            # รายการ RSS feed URL + สำนักข่าว + ภาษา
│   └── provinces.yaml        # 17 จังหวัด + คำพ้อง (ไทย/อังกฤษ)
├── news_report/
│   ├── __init__.py
│   ├── fetcher.py            # ดึง+parse RSS ทุก feed
│   ├── translator.py         # แปลข่าวที่ไม่ใช่ภาษาไทยเป็นไทย (deep-translator)
│   ├── province_filter.py    # กรองข่าวที่พาดพิงจังหวัดเป้าหมาย
│   ├── summarizer.py         # สรุปแบบง่าย (strip HTML, ตัดความยาว) + จัดรูปแบบอ้างอิงแหล่งข่าว
│   ├── storage.py            # SQLite กันข่าวซ้ำ + เก็บประวัติรายวัน
│   ├── site_generator.py     # render static HTML (Jinja2) -> docs/site
│   ├── notifier.py           # ส่ง broadcast ผ่าน LINE Messaging API
│   └── main.py               # orchestrator: fetch -> translate -> filter -> summarize -> เก็บ -> เว็บ -> แจ้งเตือน
├── templates/
│   ├── index.html            # หน้ารวมรายงานล่าสุด/ย้อนหลัง
│   └── daily.html            # หน้ารายงานของแต่ละวัน (แยกตามจังหวัด, มีลิงก์อ้างอิงต้นฉบับ)
├── docs/site/                # ผลลัพธ์ static site (สำหรับ GitHub Pages)
├── data/
│   ├── seen.db                # SQLite เก็บ id ข่าวที่ประมวลผลแล้ว
│   └── reports/YYYY-MM-DD.json  # ผลลัพธ์รายวัน
├── .github/workflows/
│   └── daily-report.yml      # cron รันทุกวัน 07:00 น.
├── tests/
│   ├── test_fetcher.py
│   ├── test_translator.py
│   ├── test_province_filter.py
│   └── test_summarizer.py
├── requirements.txt
└── README.md
```

## 6. Pipeline การทำงานรายวัน (`main.py`)
1. โหลด `feeds.yaml` และ `provinces.yaml`
2. ดึงข่าวทุก feed ด้วย `feedparser` → ได้ list ของ (title, link, summary, published, source, language)
3. ข้ามข่าวที่เคยเห็นแล้ว (เช็คจาก `link`/`guid` ใน SQLite)
4. ถ้า `language != th` → ใช้ `translator.py` แปล title + summary เป็นไทย
   (เก็บข้อความต้นฉบับไว้ด้วยเผื่ออ้างอิง/debug)
5. ใช้ `province_filter.py` ตรวจ title+summary (ฉบับไทย) ว่ามีชื่อจังหวัด (หรือคำพ้อง) ใน 17 จังหวัดหรือไม่
   - เก็บ tag จังหวัดที่ match ไว้กับข่าวนั้น (ข่าวหนึ่งอาจ match หลายจังหวัด)
6. ข่าวที่ผ่านตัวกรอง → `summarizer.py` ทำความสะอาด HTML, ตัดสรุปให้สั้นลง และแนบ **อ้างอิง**
   (ชื่อสำนักข่าวต้นฉบับ + ลิงก์ต้นฉบับ)
7. บันทึกผลลัพธ์ของวันนั้นเป็น JSON (`data/reports/YYYY-MM-DD.json`) จัดกลุ่มตามจังหวัด
8. `site_generator.py` render หน้า HTML ใหม่จาก JSON ทั้งหมด (รายวัน + หน้ารวม) ไปที่ `docs/site/`
9. `notifier.py` ส่งสรุปย่อ (จำนวนข่าวใหม่ต่อจังหวัด + ลิงก์ไปหน้าเว็บฉบับเต็ม) ผ่าน LINE OA broadcast
10. บันทึก id ข่าวที่ประมวลผลแล้วลง SQLite กันซ้ำในรอบถัดไป

## 7. การเผยแพร่ผลลัพธ์
- **Static site**: render เป็น HTML ใน `docs/site/` แล้วเปิดใช้ GitHub Pages (source: `docs/`)
  หน้าเว็บแสดงข่าวแยกตามจังหวัด + วันที่ ย้อนหลังได้ พร้อมลิงก์อ้างอิงแหล่งข่าวต้นฉบับทุกข่าว
- **LINE OA**: broadcast สรุปย่อผ่าน LINE Messaging API (ต้องใช้ `LINE_CHANNEL_ACCESS_TOKEN`
  เก็บใน GitHub Secrets)

## 8. การตั้งเวลาอัตโนมัติ
- ใช้ GitHub Actions: `.github/workflows/daily-report.yml`
- `schedule: cron: "0 0 * * *"` (00:00 UTC = **07:00 น. เวลาไทย**)
- ขั้นตอนใน workflow: checkout → setup python → pip install -r requirements.txt → รัน `python -m news_report.main`
  → commit ผลลัพธ์ (`docs/site/`, `data/`) กลับเข้า repo → push

## 9. แผนการทดสอบ
- `test_fetcher.py`: mock RSS response, ตรวจว่า parse ได้ครบ field (รวม feed ภาษาอังกฤษ)
- `test_translator.py`: ตรวจว่าข่าวภาษาอังกฤษถูกแปลเป็นไทย และเก็บต้นฉบับ+อ้างอิงไว้ถูกต้อง
  (mock การเรียก translator เพื่อไม่พึ่งพา network ตอนรัน CI)
- `test_province_filter.py`: ตรวจว่าข่าวที่มี/ไม่มีชื่อจังหวัด (รวมคำพ้อง) ถูกกรองถูกต้อง,
  ข่าวไม่เกี่ยวข้องกับ 17 จังหวัดถูกตัดออก
- `test_summarizer.py`: ตรวจว่าลบ HTML tag, ตัดความยาว และแนบอ้างอิงถูกต้อง
- ทดสอบ end-to-end ด้วย feed ตัวอย่างจริง (ทั้งไทยและอังกฤษ) 2-3 แหล่งก่อน deploy จริง

## 10. Milestones
1. **Phase 1 — Core pipeline**: fetcher + province_filter + summarizer + storage (feed ไทยก่อน, ทดสอบ local)
2. **Phase 2 — Translation**: translator.py + รวม feed ต่างประเทศเข้า pipeline
3. **Phase 3 — Static site**: site_generator + templates + ตั้งค่า GitHub Pages
4. **Phase 4 — LINE OA notification**: สร้าง LINE OA (ถ้ายังไม่มี) + notifier.py + ทดสอบ broadcast
5. **Phase 5 — Automation**: GitHub Actions workflow (cron 07:00 น.) + secrets + ทดสอบรันจริงตามตาราง
6. **Phase 6 — ปรับแต่ง**: ขยาย/ปรับรายชื่อ feed, ปรับ threshold การกรอง, ปรับข้อความ broadcast ตามฟีดแบ็ก

## 11. สิ่งที่ต้องเตรียมจากผู้ใช้ก่อน Phase 4
- LINE Official Account (ถ้ายังไม่มี ต้องสร้างที่ LINE Developers Console) และ Channel Access Token
- ยืนยัน GitHub Pages เปิดใช้งานสำหรับ repo นี้ได้ (source: `docs/`)
