# วิธี Deploy บน Mac mini (CHUEY-Server) — สำหรับข้อมูลงานความมั่นคง

รันบนเครื่องที่คุณคุมเอง (Mac mini + ฮาร์ดดิสก์ USB) ในเครือข่ายภายใน **ไม่เปิดออกอินเทอร์เน็ต**
และ **ไม่ใช้ Google Sheets** — เว็บปลายทางดึงข้อมูลผ่าน JSON API ภายในเครือข่าย LAN เดียวกันแทน
เหมาะกับข้อมูลชั้นความลับมากกว่าคลาวด์ต่างประเทศ

> ⚠️ **สำคัญ**: ตั้งค่านี้ให้เข้าถึงได้ **เฉพาะในเครือข่ายภายใน/VPN** เท่านั้น อย่าเปิด port
> forwarding ออกอินเทอร์เน็ตสาธารณะ

---

## 0. เตรียม Mac mini
- ต่อฮาร์ดดิสก์ USB ไว้ (สมมติชื่อไดรฟ์ว่า `CHUEY` → path จะเป็น `/Volumes/CHUEY`)
- เปิด **Terminal** (Applications → Utilities → Terminal)

## 1. ติดตั้ง Homebrew + Python + Git (ครั้งเดียว)
```bash
# ติดตั้ง Homebrew (ถ้ายังไม่มี)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
# ติดตั้ง python + git
brew install python git
```

## 2. ดึงโค้ด (เก็บโปรเจกต์ไว้บนฮาร์ดดิสก์ USB)
```bash
cd /Volumes/CHUEY
git clone https://github.com/chuey5910/News_Report.git
cd News_Report
git checkout claude/news-reporting-app-mvo1r6
python3 -m venv .venv
source .venv/bin/activate
pip install -r report_center/requirements.txt
pip install gunicorn        # ตัวรันเว็บสำหรับใช้งานจริง
```

## 3. ตั้งค่า .env (เก็บฐานข้อมูลบนฮาร์ดดิสก์ USB, ปิด Google Sheets)
สร้างไฟล์ `report_center/.env` (เช่น `nano report_center/.env`) ใส่:
```
SECRET_KEY=ใส่ข้อความสุ่มยาวๆของคุณเอง
REPORT_CENTER_API_KEY=ใส่คีย์ลับสำหรับให้เว็บปลายทางดึง API
DATABASE_URL=sqlite:////Volumes/CHUEY/News_Report/data/report_center.db
# ไม่ใส่ GOOGLE_SHEETS_* = ปิด sync Google Sheets โดยสมบูรณ์ (ข้อมูลไม่ออกนอกเครื่อง)
```
> สร้างโฟลเดอร์เก็บ db ก่อน: `mkdir -p /Volumes/CHUEY/News_Report/data`
> (`sqlite:////` มี 4 ขีด เพราะตามด้วย path เต็มที่ขึ้นต้นด้วย `/`)

## 4. สร้างบัญชี admin คนแรก
```bash
export FLASK_APP=report_center
flask create-admin admin "ผู้ดูแลระบบ"
```

## 5. หา IP ของ Mac mini ในเครือข่าย (ให้เครื่องอื่นเข้าถึง)
```bash
ipconfig getifaddr en0    # สาย LAN; ถ้าใช้ Wi-Fi ลอง en1
```
สมมติได้ `192.168.1.50`

## 6. รันเว็บ (ผูกกับเครือข่ายภายใน)
```bash
cd /Volumes/CHUEY/News_Report
source .venv/bin/activate
export FLASK_APP=report_center
gunicorn -w 2 -b 0.0.0.0:5001 report_center.wsgi:application
```
- เปิดจาก Mac mini เอง: `http://127.0.0.1:5001`
- เปิดจากเครื่องอื่นในวง LAN: `http://192.168.1.50:5001`

## 7. ให้รันอัตโนมัติตลอด (ไม่ต้องเปิด Terminal ค้าง)
สร้างไฟล์ `~/Library/LaunchAgents/com.chuey.reportcenter.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.chuey.reportcenter</string>
  <key>WorkingDirectory</key><string>/Volumes/CHUEY/News_Report</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Volumes/CHUEY/News_Report/.venv/bin/gunicorn</string>
    <string>-w</string><string>2</string>
    <string>-b</string><string>0.0.0.0:5001</string>
    <string>report_center.wsgi:application</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict><key>FLASK_APP</key><string>report_center</string></dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/Volumes/CHUEY/News_Report/data/server.log</string>
  <key>StandardErrorPath</key><string>/Volumes/CHUEY/News_Report/data/server.err.log</string>
</dict>
</plist>
```
โหลดให้ทำงาน:
```bash
launchctl load ~/Library/LaunchAgents/com.chuey.reportcenter.plist
```

---

## เว็บปลายทางดึงข้อมูลยังไง (แทน Google Sheets)
เว็บอีกตัวในเครือข่ายเดียวกันเรียก JSON API:
```
GET http://192.168.1.50:5001/api/reports/latest
Header: X-API-Key: <REPORT_CENTER_API_KEY ที่ตั้งใน .env>
```
ข้อมูลไม่ออกนอก LAN — ปลอดภัยกว่า Google Sheets

## สำรองข้อมูลอัตโนมัติ (สำคัญมาก — ฮาร์ดดิสก์ USB คือจุดเสี่ยง)
ฐานข้อมูลทั้งหมดอยู่ในไฟล์เดียว `/Volumes/CHUEY/News_Report/data/report_center.db`
ตั้ง cron สำรองวันละครั้งไปที่ดิสก์อื่น/โฟลเดอร์อื่น เช่น (`crontab -e`):
```
0 2 * * * cp /Volumes/CHUEY/News_Report/data/report_center.db "$HOME/backup_report_$(date +\%Y\%m\%d).db"
```
> ในระยะยาว **ควรอัปเป็น NAS ที่มี RAID** เพื่อกันฮาร์ดดิสก์เสีย — ตามที่วางแผนไว้

## มาตรการความปลอดภัยที่ระบบมีให้แล้ว
- รหัสผ่าน hash, สมาชิกใหม่ต้องรออนุมัติ, แบ่งสิทธิ์ admin/user, บันทึก log การเข้าระบบทุกครั้ง
- **กัน brute-force**: ล็อกการล็อกอินชั่วคราว 15 นาที เมื่อกรอกผิด 5 ครั้งติด (ปรับได้ผ่าน env
  `LOGIN_MAX_FAILED_ATTEMPTS`, `LOGIN_LOCKOUT_MINUTES`)
- ถ้าต่อ HTTPS (เช่นผ่าน reverse proxy ภายใน) ให้ตั้ง `SESSION_COOKIE_SECURE=1` ใน `.env`

## ข้อควรระวังเฉพาะ Mac mini + USB
- ถ้าฮาร์ดดิสก์ USB หลุด/unmount ระหว่างรัน แอปจะเขียน db ไม่ได้ — ตรวจว่าไดรฟ์ mount อยู่เสมอ
- ปิด Sleep ของ Mac mini (System Settings → Energy) ไม่งั้นเครื่องหลับแล้วเว็บล่ม

---

## ใช้งานบน iPhone / iPad (แบบแอป) + ทำงานนอกสถานที่

### ก) เข้าถึงจากนอกออฟฟิศอย่างปลอดภัย — ใช้ VPN (แนะนำสำหรับข้อมูลความมั่นคง)
อย่าเปิดเว็บออกอินเทอร์เน็ตสาธารณะตรงๆ ให้ใช้ VPN แทน — iPhone/iPad เชื่อม VPN แล้วเข้าเว็บ
เหมือนอยู่ในออฟฟิศ ข้อมูลวิ่งในอุโมงค์เข้ารหัส เครื่องไม่ต้องเปิด port ออกเน็ต

**Tailscale (ง่ายสุด, ฟรี, ไม่ต้องตั้ง router):**
1. บน Mac mini: `brew install tailscale` แล้ว `sudo tailscale up` (ล็อกอินด้วยบัญชีองค์กร)
2. จด Tailscale IP ของ Mac mini (เช่น `100.x.y.z`) — `tailscale ip -4`
3. บน iPhone/iPad: ติดตั้งแอป **Tailscale** จาก App Store → ล็อกอินบัญชีเดียวกัน → เปิด VPN
4. เปิด Safari บนมือถือไปที่ `http://100.x.y.z:5001` (ใช้ได้จากทุกที่ที่เน็ตเข้าถึง โดยไม่โผล่สู่สาธารณะ)
> ทางเลือกอื่น: WireGuard บน router ของออฟฟิศ (ปลอดภัยสูง แต่ตั้งค่ายากกว่า ต้องให้ IT ช่วย)

### ข) ติดตั้งเป็น "แอป" บนหน้าจอ (PWA — ไม่ต้องโหลดจาก App Store)
บน iPhone/iPad เปิดเว็บใน **Safari** แล้ว:
1. กดปุ่ม **Share** (สี่เหลี่ยมมีลูกศรขึ้น)
2. เลือก **Add to Home Screen (เพิ่มไปยังโฮมสกรีน)**
3. กด **Add** → จะได้ไอคอนแอป "บันทึกข่าว" บนหน้าจอ เปิดแล้วเต็มจอเหมือนแอปจริง

หน้าเว็บออกแบบให้ใช้บนมือถือได้ลื่น (ฟอร์มเรียงคอลัมน์เดียวอัตโนมัติ) — ทำงานได้ทั้ง iPhone และ iPad
