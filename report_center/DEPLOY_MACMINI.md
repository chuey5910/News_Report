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

> ⚠️ **สำคัญ (บทเรียนจากการติดตั้งจริง)**: macOS รุ่นใหม่บล็อกไม่ให้โปรแกรมที่รัน
> เบื้องหลังผ่าน launchd อ่านไฟล์บน**ฮาร์ดดิสก์ USB** (ขึ้น
> `PermissionError: Operation not permitted` และ launchctl โชว์รหัส 78/1)
> ต้องทำ 3 อย่าง: (ก) เรียกผ่าน `/bin/bash -c`, (ข) เก็บ log ไว้ในดิสก์ภายใน
> ไม่ใช่บน USB, (ค) ให้สิทธิ์ **Full Disk Access** กับ `/bin/bash`

สร้างไฟล์ plist (แทน `USERNAME` ด้วยชื่อผู้ใช้เครื่อง — ดูได้จาก `whoami`):
```bash
cat > ~/Library/LaunchAgents/com.chuey.reportcenter.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.chuey.reportcenter</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-c</string>
    <string>cd /Volumes/CHUEY/News_Report && exec .venv/bin/gunicorn -w 2 -b 0.0.0.0:5001 report_center.wsgi:application</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/Users/USERNAME/reportcenter.log</string>
  <key>StandardErrorPath</key><string>/Users/USERNAME/reportcenter.err.log</string>
</dict>
</plist>
EOF
```

ให้สิทธิ์ Full Disk Access กับ bash (ครั้งเดียว):
1. **System Settings → Privacy & Security → Full Disk Access**
2. กด `+` → กด **Cmd+Shift+G** → พิมพ์ `/bin/bash` → Enter → **Open**
3. ตรวจว่าสวิตช์ของ `bash` เป็น ON
4. ตรวจใน **System Settings → General → Login Items & Extensions** ส่วน
   "Allow in the Background" ว่ารายการ `bash` เปิดอยู่ด้วย

โหลดให้ทำงาน แล้วตรวจสถานะ:
```bash
launchctl load ~/Library/LaunchAgents/com.chuey.reportcenter.plist
sleep 3
launchctl list | grep reportcenter    # ต้องขึ้นตัวเลข PID เช่น "32476  0  com.chuey.reportcenter"
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5001/   # ต้องได้ 302
```
ถ้าคอลัมน์แรกเป็น `-` (ไม่ใช่ตัวเลข) = ยังล้มอยู่ ให้ดูสาเหตุใน `~/reportcenter.err.log`

### วิธีอัปเดตโค้ดครั้งต่อไป (หลังตั้ง launchd แล้ว)
```bash
cd /Volumes/CHUEY/News_Report && git pull
launchctl kickstart -k gui/$(id -u)/com.chuey.reportcenter
```

### คำสั่งดูแลระบบที่ใช้บ่อย
```bash
launchctl list | grep reportcenter     # ดูสถานะ (ตัวเลข = รันอยู่)
launchctl unload ~/Library/LaunchAgents/com.chuey.reportcenter.plist   # ปิดเว็บ
launchctl load ~/Library/LaunchAgents/com.chuey.reportcenter.plist     # เปิดเว็บ
> ~/reportcenter.err.log               # ล้างไฟล์ log (ไฟล์ log เป็นข้อความล้วน กินที่น้อยมาก)
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

## แจ้งเตือนผ่าน LINE OA (ทางเลือก)

ระบบส่งแจ้งเตือนเข้า LINE ได้ 2 แบบ: **ทันทีเมื่อมีข่าวล่วงหน้าใหม่** และ **สรุปกิจกรรมวันนี้ทุกเช้า**
ปิดสนิทโดยค่าเริ่มต้น — เปิดเมื่อใส่ token ใน `.env` เท่านั้น และส่งเฉพาะข้อมูลขั้นต่ำ
(ชื่อกิจกรรม จังหวัด วันเวลา + ลิงก์) รายละเอียดลับต้องล็อกอิน+VPN เข้าระบบเอง

> 💡 **แนะนำให้สร้าง LINE OA ใหม่แยกต่างหาก** สำหรับงานนี้ (ฟรี) — ไม่ยุ่งกับ OA
> เดิมที่ระบบอื่นใช้อยู่เลย: โควตาข้อความแยกกัน, ตั้งค่า webhook ไม่ชนกัน และ
> broadcast ได้ปลอดภัยเพราะเพื่อนของ OA มีแต่คนในทีม

ขั้นตอน:
1. สร้าง OA ที่ https://manager.line.biz → สร้างบัญชีใหม่ (ฟรี)
2. เปิดใช้ Messaging API: LINE Developers Console (https://developers.line.biz)
   → สร้าง/เลือก channel ของ OA → แท็บ **Messaging API** → **Issue** ตรง
   Channel access token (long-lived) → คัดลอก token
3. ใส่ใน `report_center/.env`:
   ```
   LINE_CHANNEL_ACCESS_TOKEN=<token ที่ได้>
   REPORT_CENTER_BASE_URL=http://100.x.y.z:5001   # Tailscale IP ของ Mac mini
   ```
   (ไม่ตั้ง LINE_TARGET_IDS = broadcast หาทุกคนที่เป็นเพื่อน OA)
4. ให้ทุกคนในทีมแอด OA เป็นเพื่อน (สแกน QR จากหน้า LINE Official Account Manager)
5. รีสตาร์ทเว็บ: `launchctl kickstart -k gui/$(id -u)/com.chuey.reportcenter`
6. ตั้งเวลาส่งอัตโนมัติ (วางทีละบรรทัดใน Terminal — เพิ่มเข้าตาราง cron ให้เอง):
   - **สรุปทุกเช้า 7 โมง** (กิจกรรมวันนี้ + ล่วงหน้า 7 วัน):
     ```bash
     (crontab -l 2>/dev/null; echo '0 7 * * * cd /Volumes/CHUEY/News_Report && .venv/bin/flask --app report_center line-daily >> $HOME/line-daily.log 2>&1') | crontab -
     ```
   - **แจ้งเตือนเมื่อถึงกำหนดเวลาทำกิจกรรม** (ตรวจทุก 5 นาที ส่งครั้งเดียวต่อกิจกรรม):
     ```bash
     (crontab -l 2>/dev/null; echo '*/5 * * * * cd /Volumes/CHUEY/News_Report && .venv/bin/flask --app report_center line-due >> $HOME/line-due.log 2>&1') | crontab -
     ```
   ตรวจรายการที่ตั้งไว้: `crontab -l`

ทดสอบส่งทันที: `cd /Volumes/CHUEY/News_Report && .venv/bin/flask --app report_center line-daily`

> หมายเหตุโควตา: LINE OA แผนฟรีส่งได้จำกัดต่อเดือน (ประมาณ 300 ข้อความ โดยนับ
> ตามจำนวนผู้รับ) — ถ้าทีมมีสมาชิกหลายคนและแจ้งเตือนถี่ อาจต้องอัปแผนหรือลดความถี่

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
