# News_Report

ระบบดึงข่าวจาก RSS (ทุกสำนักข่าว ทั้งไทยและต่างประเทศ) มากรองเฉพาะข่าวที่เกี่ยวข้องกับ
17 จังหวัดภาคเหนือ/เหนือตอนล่าง สรุปแบบง่าย (ไม่ใช้ AI) พร้อมอ้างอิงแหล่งข่าวต้นฉบับ
เผยแพร่เป็นเว็บสรุปรายวัน (GitHub Pages) และแจ้งเตือนผ่าน LINE Official Account
ทุกวันเวลา 07:00 น. โดยอัตโนมัติผ่าน GitHub Actions

รายละเอียดการออกแบบทั้งหมดอยู่ที่ [`docs/FEATURE_X_PLAN.md`](docs/FEATURE_X_PLAN.md)

## จังหวัดเป้าหมาย (17 จังหวัด)
เชียงใหม่, เชียงราย, ลำพูน, ลำปาง, พะเยา, แพร่, น่าน, แม่ฮ่องสอน, ตาก,
สุโขทัย, อุตรดิตถ์, กำแพงเพชร, พิษณุโลก, พิจิตร, เพชรบูรณ์, นครสวรรค์, อุทัยธานี

แก้ไขรายชื่อจังหวัด/คำพ้องได้ที่ `config/provinces.yaml`
แก้ไขรายชื่อ RSS feed ได้ที่ `config/feeds.yaml` (ไม่ต้องแก้โค้ด)

## รันในเครื่อง (local)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# รันทดสอบหน่วย (ไม่ต้องต่อเน็ต, ไม่ต้องมี LINE token)
pytest

# รัน pipeline จริง (ต้องต่อเน็ตเพื่อดึง RSS จริง)
python -m news_report.main
```

ผลลัพธ์จะถูกเขียนไปที่:
- `data/seen.db` — กันข่าวซ้ำระหว่างรอบ
- `data/reports/<YYYY-MM-DD>.json` — ผลสรุปของแต่ละวัน จัดกลุ่มตามจังหวัด
- `docs/site/` — เว็บสรุปข่าวแบบ static (สำหรับ GitHub Pages)

ถ้ายังไม่ตั้งค่า `LINE_CHANNEL_ACCESS_TOKEN` ขั้นตอนแจ้งเตือน LINE จะ log error แล้วข้ามไป
โดยไม่ทำให้ pipeline ล้มเหลว (ไฟล์รายงาน/เว็บยังถูกสร้างตามปกติ)

## ตั้งค่าเพื่อรันอัตโนมัติบน GitHub
1. **เปิด GitHub Pages**: Settings → Pages → Source: Deploy from a branch → เลือก branch ที่ deploy
   จริง + โฟลเดอร์ `/docs`
2. **ตั้งค่า Secret**: Settings → Secrets and variables → Actions → New repository secret
   - `LINE_CHANNEL_ACCESS_TOKEN` — Channel access token (long-lived) จาก LINE Developers Console
     ของ LINE OA ที่ต้องการ broadcast (ดูวิธีเอา token ในแชทที่คุยกันไว้)
3. **ตั้งค่า Variable (ไม่ใช่ secret เพราะไม่ใช่ข้อมูลลับ)**: Settings → Secrets and variables →
   Actions → Variables → New repository variable
   - `SITE_BASE_URL` — URL ของ GitHub Pages เช่น `https://<user>.github.io/News_Report`
     (ใช้แนบลิงก์ไปหน้าเว็บในข้อความ broadcast)
4. **รันครั้งแรกด้วยมือ** เพื่อ seed เว็บเพจตั้งต้น: Actions → Daily News Report → Run workflow
   (ก่อนถึงรอบ cron เว็บ Pages จะยังไม่มีอะไรให้แสดง)

หลังจากนั้นระบบจะรันอัตโนมัติทุกวันเวลา 07:00 น. เวลาไทย (`.github/workflows/daily-report.yml`)

## หมายเหตุสำคัญ
- รายชื่อ RSS feed ใน `config/feeds.yaml` เป็นตัวอย่างเริ่มต้น **ควรตรวจสอบว่า URL ยังใช้งานได้จริง**
  ก่อนพึ่งพาใช้งานจริง เพราะ feed อาจเปลี่ยน URL หรือปิดตัวได้โดยไม่แจ้งล่วงหน้า
- การแปลข่าวต่างประเทศใช้ `deep-translator` (ครอบ Google Translate แบบไม่เป็นทางการ ไม่ต้องขอ
  API key) จึงไม่มี SLA รับประกันความเสถียร มี retry ในตัว แต่ถ้าพบปัญหาใช้งานไม่ได้บ่อยในระยะยาว
  ให้พิจารณาเปลี่ยนไปใช้ DeepL หรือ Google Cloud Translation API แทน
- LINE Notify ถูกยกเลิกไปแล้วตั้งแต่ 31 มี.ค. 2025 ระบบนี้ใช้ **LINE Messaging API**
  (Broadcast Message) ของ LINE OA แทน
