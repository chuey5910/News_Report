# วิธี Deploy ขึ้น PythonAnywhere (ฟรี, มี URL ถาวร)

เหมาะกับมือใหม่ที่สุด — ทำทุกอย่างผ่านเว็บ ไม่ต้องติดตั้ง Python/Git ในเครื่องตัวเอง
ข้อมูล SQLite ไม่หาย และเข้า Google Sheets API ได้

> เตรียมให้พร้อมก่อน: บัญชี GitHub ที่มีโค้ดนี้ (`chuey5910/News_Report`), ไฟล์ service-account JSON
> ของ Google, และ Spreadsheet ID (แชร์ Sheet ให้ service account email เรียบร้อยแล้ว)

## 1. สมัคร PythonAnywhere (ฟรี)
- ไปที่ https://www.pythonanywhere.com/ → **Pricing & signup** → **Create a Beginner account** (ฟรี)
- ยืนยันอีเมล แล้วล็อกอิน

## 2. ดึงโค้ดลงเซิร์ฟเวอร์ (ผ่าน Bash console บนเว็บ)
- แท็บ **Consoles** → **Bash** (เปิด terminal บนเว็บ)
- พิมพ์:
  ```bash
  git clone https://github.com/chuey5910/News_Report.git
  cd News_Report
  git checkout claude/news-reporting-app-mvo1r6
  ```

## 3. สร้าง virtualenv + ติดตั้ง dependencies
  ```bash
  python3.10 -m venv .venv
  source .venv/bin/activate
  pip install -r report_center/requirements.txt
  ```
  (PythonAnywhere มี python3.10 อยู่แล้ว ถ้าเวอร์ชันต่างไปให้ปรับเลข)

## 4. อัปโหลดไฟล์ Google credentials + สร้าง .env
- แท็บ **Files** → เข้าโฟลเดอร์ `News_Report/report_center/` → **Upload a file** → อัปโหลดไฟล์
  service-account JSON → เปลี่ยนชื่อเป็น `service-account.json`
- ยังอยู่ในโฟลเดอร์ `report_center/` → **New file** ชื่อ `.env` → ใส่เนื้อหา (แก้ค่าให้ถูก):
  ```
  SECRET_KEY=ใส่ข้อความสุ่มยาวๆของคุณเอง
  REPORT_CENTER_API_KEY=ใส่คีย์ที่ตั้งเอง
  GOOGLE_SHEETS_SPREADSHEET_ID=16_HFkdU7IsyU9RZQcsH5hFqJ9gk2YI-8sIO0mjUrtl0
  GOOGLE_SHEETS_CREDENTIALS_FILE=/home/<ชื่อผู้ใช้ PythonAnywhere>/News_Report/report_center/service-account.json
  GOOGLE_SHEETS_WORKSHEET=reports
  ```
  > `GOOGLE_SHEETS_CREDENTIALS_FILE` ต้องเป็น path เต็ม แทน `<ชื่อผู้ใช้>` ด้วยชื่อบัญชีจริง

## 5. สร้างบัญชี admin คนแรก (ใน Bash console)
  ```bash
  cd ~/News_Report
  source .venv/bin/activate
  export FLASK_APP=report_center
  flask create-admin admin "ผู้ดูแลระบบ"
  ```
  (พิมพ์รหัสผ่าน 2 ครั้ง)

## 6. ตั้งค่า Web app
- แท็บ **Web** → **Add a new web app** → **Manual configuration** → เลือก **Python 3.10**
- ในหน้าตั้งค่า web app หัวข้อ **Virtualenv** → ใส่ path:
  `/home/<ชื่อผู้ใช้>/News_Report/.venv`
- หัวข้อ **Code → WSGI configuration file** → คลิกเข้าไปแก้ ให้ลบของเดิมทิ้ง แล้วใส่:
  ```python
  import sys
  path = "/home/<ชื่อผู้ใช้>/News_Report"
  if path not in sys.path:
      sys.path.insert(0, path)

  from report_center.wsgi import application  # noqa
  ```
- กด **Save** แล้วกลับมาหน้า Web → กดปุ่ม **Reload** (เขียวๆ)

## 7. เปิดใช้งาน
- URL ของคุณคือ `https://<ชื่อผู้ใช้>.pythonanywhere.com`
- เปิด → login ด้วย `admin` → บันทึกรายงาน 1 อัน → เปิด Google Sheet ดูว่ามีแถวขึ้นมาไหม

## ดันข้อมูลเก่าขึ้น Sheet ทีเดียว (ถ้ามี)
  ```bash
  cd ~/News_Report && source .venv/bin/activate && export FLASK_APP=report_center
  flask sync-sheets
  ```

## เวลาแก้โค้ดใหม่แล้วอยากอัปเดตเว็บ
  ```bash
  cd ~/News_Report && git pull && source .venv/bin/activate
  pip install -r report_center/requirements.txt   # เฉพาะตอนมี dependency ใหม่
  ```
  แล้วไปแท็บ **Web** → กด **Reload**

## แก้ปัญหาที่พบบ่อย
- **เว็บขึ้น error** → แท็บ **Web** → ดู **Error log** (ลิงก์ท้ายหน้า)
- **sync ขึ้น Sheet ไม่ได้** → เช็ก 3 อย่าง: (1) แชร์ Sheet ให้ service-account email เป็น Editor แล้ว
  (2) path ไฟล์ JSON ใน `.env` ถูกต้อง (3) เปิด Google Sheets API ใน Google Cloud แล้ว
- **ฟรีแอคเคาต์เข้าเน็ตภายนอกไม่ได้** → Google APIs (`googleapis.com`) อยู่ใน whitelist ของ
  PythonAnywhere อยู่แล้ว จึงใช้ได้ ไม่ต้องทำอะไรเพิ่ม

---

## ทางเลือกอื่น (ถ้าไม่ใช้ PythonAnywhere)
- **Render.com** — ฟรี แต่ SQLite จะหายเมื่อ redeploy/sleep (ต้องต่อ Postgres แยก) เหมาะกว่าถ้าอยาก
  ใช้ฐานข้อมูลจริงจัง — บอกผมได้ถ้าอยากได้คู่มือ Render + Postgres
- รันบนเซิร์ฟเวอร์/VPS ของตัวเอง — ใช้ `gunicorn report_center.wsgi:application` หลัง nginx
