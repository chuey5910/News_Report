# ติดตั้งระบบรายงานข่าวบน NAS (UGREEN DXP4800 Plus + Docker)

คู่มือนี้ใช้แทน `DEPLOY_MACMINI.md` เมื่อย้ายมารันบน NAS
ระบบจะแยกเป็น 2 คอนเทนเนอร์ ใช้อิมเมจเดียวกัน อ่านค่าตั้งจากไฟล์ `.env` ไฟล์เดียว

| คอนเทนเนอร์ | หน้าที่ | แทนอะไรบน Mac mini |
|---|---|---|
| `news-report-web` | หน้าเว็บ (gunicorn พอร์ต 5001) | launchd + gunicorn |
| `news-report-scheduler` | แจ้งเตือน LINE ตามเวลา | crontab ของเครื่อง |

> **ยังไม่ต้องปิดระบบบน Mac mini** จนกว่าจะทดสอบบน NAS ผ่านทุกข้อในหัวข้อ 7

---

## 1. เตรียมโฟลเดอร์บน NAS

เปิด **Terminal/SSH** ของ NAS (UGOS → ตั้งค่า → Terminal & SNMP → เปิด SSH) แล้ว:

```bash
# ตรวจว่าชื่อ volume คืออะไร (มักเป็น /volume1 หรือ /volume2)
ls /volume*

# สร้างที่เก็บระบบ (แก้ /volume1 ตามที่เห็นจากคำสั่งข้างบน)
mkdir -p /volume1/docker
cd /volume1/docker
git clone https://github.com/chuey5910/News_Report.git news_report
cd news_report
git checkout claude/news-reporting-app-mvo1r6

# โฟลเดอร์เก็บฐานข้อมูลและไฟล์ความลับ
mkdir -p data secrets
```

## 2. ตั้งค่าในไฟล์ `.env`

```bash
cp report_center/.env.example report_center/.env
nano report_center/.env
```

ค่าที่**ต้อง**ใส่ (ลอกค่าเดิมจาก Mac mini ได้เลย ดูวิธีในหัวข้อ 3):

```ini
# ฐานข้อมูลอยู่ในโฟลเดอร์ data ที่ mount เข้าคอนเทนเนอร์ (4 ขีดเพราะเป็น path เต็ม)
DATABASE_URL=sqlite:////data/report_center.db

SECRET_KEY=<ข้อความสุ่มยาวๆ อันเดิมจาก Mac mini>
REPORT_CENTER_API_KEY=<อันเดิมจาก Mac mini>

# Google Sheets — ไฟล์ credential ต้องอยู่ในโฟลเดอร์ secrets
GOOGLE_SHEETS_SPREADSHEET_ID=<อันเดิม>
GOOGLE_SHEETS_CREDENTIALS_FILE=secrets/service-account.json
GOOGLE_SHEETS_WORKSHEET=reports

# LINE
LINE_CHANNEL_ACCESS_TOKEN=<อันเดิม>
LINE_TARGET_IDS=<groupId เดิม ขึ้นต้นด้วย C>
REPORT_CENTER_BASE_URL=http://<ชื่อหรือ IP ของ NAS ใน Tailscale>:5001
```

> `REPORT_CENTER_BASE_URL` คือลิงก์ที่ไปโผล่ในข้อความไลน์ — ใส่ชื่อเครื่องใน Tailscale
> (เช่น `http://ugreen-nas:5001`) จะดีกว่าใส่เลข IP เพราะย้ายเครื่องอีกก็ไม่ต้องแก้

## 3. ย้ายข้อมูลจาก Mac mini

**บน Mac mini** — ส่ง 3 ไฟล์ไป NAS (แก้ `USER@NAS-IP` ตามของจริง):

```bash
cd /Volumes/CHUEY-Server/News_Report
scp report_center/instance/report_center.db USER@NAS-IP:/volume1/docker/news_report/data/report_center.db
scp report_center/service-account.json      USER@NAS-IP:/volume1/docker/news_report/secrets/
cat report_center/.env      # เปิดดูเพื่อลอกค่าไปใส่ใน .env ของ NAS (หัวข้อ 2)
```

> ถ้าไฟล์ฐานข้อมูลอยู่ path อื่น หาด้วย: `grep DATABASE_URL report_center/.env`
> (ถ้าไม่ได้ตั้งไว้ ค่าเริ่มต้นคือ `report_center/instance/report_center.db`)

## 4. เปิดระบบ

```bash
cd /volume1/docker/news_report
docker compose up -d --build      # ครั้งแรกใช้เวลา 2-5 นาที (ติดตั้ง dependency)
docker compose ps                 # ทั้ง 2 ตัวต้องขึ้น Up / healthy
```

ตรวจว่าเว็บตอบจริง (ต้องได้ `302`):
```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5001/
```

## 5. สร้าง/กู้บัญชีผู้ใช้

ถ้าย้ายฐานข้อมูลเดิมมาแล้ว บัญชีทั้งหมดตามมาด้วย ตรวจได้ด้วย:
```bash
docker compose exec web flask --app report_center list-users
```
ถ้าลืมรหัส หรือเริ่มใหม่จากฐานข้อมูลเปล่า:
```bash
docker compose exec web flask --app report_center reset-password admin
docker compose exec web flask --app report_center create-admin admin "ผู้ดูแลระบบ"   # กรณีไม่มีบัญชีเลย
```

## 6. ให้เข้าถึงผ่าน Tailscale

คอนเทนเนอร์ web เปิดพอร์ต 5001 ที่ตัว NAS ดังนั้น:

- **ถ้าคอนเทนเนอร์ Tailscale รันแบบ host network** (พบบ่อยสุด) — ใช้งานได้เลย
  เข้าจากมือถือที่ `http://<ชื่อ NAS ใน Tailscale>:5001`
- ดูชื่อ/IP ของ NAS ในเครือข่าย Tailscale:
  ```bash
  docker exec <ชื่อคอนเทนเนอร์-tailscale> tailscale status
  docker exec <ชื่อคอนเทนเนอร์-tailscale> tailscale ip -4
  ```
- ถ้าเข้าไม่ได้ ให้ตรวจว่าคอนเทนเนอร์ Tailscale ตั้ง `network_mode: host` หรือทำเป็น subnet router
  ให้เห็นเครือข่ายบ้าน (`--advertise-routes`) — ถ้าไม่ใช่ทั้งสองแบบ เครื่องอื่นจะเห็นแต่ตัวคอนเทนเนอร์ ไม่เห็นเว็บ

**แชร์ให้พนักงาน** — ทำเหมือนเดิมแต่เปลี่ยนเป็นเครื่อง NAS:
login.tailscale.com/admin/machines → เครื่อง NAS → ⋯ → **Share...** → ส่งลิงก์ให้เจ้าตัว

## 7. รายการทดสอบก่อนปิดระบบบน Mac mini

ทำให้ครบทุกข้อ ค่อยปิดของเก่า:

- [ ] เข้าเว็บจากมือถือผ่าน Tailscale ได้
- [ ] ล็อกอินด้วยบัญชีเดิมได้ และเห็นรายงานเก่าครบ
- [ ] บันทึกรายงานใหม่ได้ทั้ง 3 แท็บ (ล่วงหน้า/ปิดข่าว/เหตุการณ์)
- [ ] แถวใหม่ขึ้นใน Google Sheet
- [ ] `docker compose exec web flask --app report_center line-status` — โหมดส่งขึ้น "เข้ากลุ่ม"
- [ ] ทดลองส่งสรุป: `docker compose exec web flask --app report_center line-daily` แล้วเข้าไลน์จริง
- [ ] `docker logs news-report-scheduler` — เห็นบรรทัด "แจ้งเตือนถึงเวลากิจกรรม" เดินทุก 5 นาที
- [ ] ปิด-เปิด NAS แล้วทั้ง 2 คอนเทนเนอร์กลับมาเองโดยไม่ต้องสั่ง

**ปิดระบบบน Mac mini** (ทำหลังผ่านครบแล้ว — ยังไม่ต้องลบไฟล์ เก็บไว้เป็นสำรองอีก 2-4 สัปดาห์):
```bash
launchctl unload ~/Library/LaunchAgents/com.chuey.reportcenter.plist
crontab -r        # ลบงานแจ้งเตือน (กันส่งซ้ำ 2 เครื่อง) — ดูของเดิมก่อนด้วย crontab -l
```

---

## คำสั่งที่ใช้บ่อย

```bash
cd /volume1/docker/news_report

docker compose ps                          # สถานะ
docker compose logs -f web                 # log หน้าเว็บ
docker compose logs -f scheduler           # log แจ้งเตือน LINE
docker compose restart web                 # รีสตาร์ทเว็บ
docker compose down                        # ปิดทั้งระบบ
docker compose up -d                       # เปิดทั้งระบบ

# อัปเดตโค้ดเวอร์ชันใหม่
git pull && docker compose up -d --build

# สำรองฐานข้อมูล (ทำก่อนอัปเดตใหญ่ทุกครั้ง)
cp data/report_center.db data/report_center.db.$(date +%Y%m%d)
```

## หมายเหตุ

- **ฐานข้อมูลอยู่ที่ `data/report_center.db`** บน NAS — ควรตั้งงานสำรองของ UGOS ให้ copy
  โฟลเดอร์ `data/` ขึ้นคลาวด์หรือดิสก์อื่นเป็นระยะ (RAID 1 กันดิสก์เสีย แต่ไม่กันลบผิด/ไฟไหม้)
- เวลาในคอนเทนเนอร์ตั้งเป็น `Asia/Bangkok` แล้ว จึงส่งสรุป 07:00 ตามเวลาไทยถูกต้อง
- คอนเทนเนอร์ทั้งสองเขียนไฟล์ฐานข้อมูลเดียวกัน โค้ดเปิดโหมด WAL และรอคิวสูงสุด 30 วินาที
  ให้แล้ว จึงไม่เกิด `database is locked`
- ระบบฟังแค่พอร์ต 5001 บน NAS ไม่ได้เปิดออกอินเทอร์เน็ต — เข้าถึงได้ผ่าน Tailscale
  หรือเครือข่ายบ้านเท่านั้น **ห้ามตั้ง port forward บนเราเตอร์**
