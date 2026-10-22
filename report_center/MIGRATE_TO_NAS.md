# ย้ายระบบจาก Mac mini ไป NAS — ทำจาก Terminal ของ Mac mini เครื่องเดียว

**วิธีทำงาน:** รีโมทเข้า Mac mini (ที่ทำงาน) แล้วเปิด **Terminal** ของมัน → พิมพ์ทุกอย่างที่นั่น
ไฟล์ถูกส่งตรงจาก Mac mini ไป NAS ผ่าน Tailscale ไม่ต้องผ่าน MacBook
(MacBook มีหน้าที่แค่เป็นจอรีโมท และใช้เปิดหน้าเว็บ UGOS ตอนขั้น 0 เท่านั้น)

ค่าประจำเครื่อง:

| อะไร | ค่า |
|---|---|
| โฟลเดอร์ระบบเดิม (บน Mac mini) | `/Volumes/CHUEY-Server/News_Report` |
| NAS ในบ้าน (LAN) | `192.168.1.51` |
| NAS ผ่าน Tailscale | หาในขั้น 1 |

**คำสั่งทุกบล็อกพิมพ์ใน Terminal ของ Mac mini** ยกเว้นบล็อกที่เขียนกำกับว่า `[ใน NAS]`
ซึ่งหมายถึงหลังจาก `ssh` เข้า NAS แล้ว (พิมพ์ในหน้าต่างเดิมนั้นต่อได้เลย)

---

## ขั้น 0 — เปิด SSH บน NAS (ครั้งเดียว)

**สิ่งที่ทำ:** เปิดช่องให้ Mac mini สั่งงาน NAS ได้

เปิดเบราว์เซอร์เข้าหน้าจัดการ NAS → **ตั้งค่า → Terminal & SNMP** → เปิด **Enable SSH**
(ทำจาก MacBook ที่บ้านสะดวกสุด เพราะอยู่วงเดียวกับ NAS: เข้า `http://192.168.1.51`)

---

## ขั้น 1 — หาที่อยู่ของ NAS ในเครือข่าย Tailscale

**สิ่งที่ทำ:** Mac mini อยู่ที่ทำงาน NAS อยู่บ้าน — คุยกันได้ผ่าน Tailscale เท่านั้น ต้องรู้ที่อยู่ก่อน

```bash
/Applications/Tailscale.app/Contents/MacOS/Tailscale status
```
มองหาบรรทัดที่เป็น NAS (ชื่อมักมีคำว่า `nas` หรือ `ugreen`) — เลขหน้าบรรทัดคือที่อยู่ เช่น `100.101.102.103`

ทดสอบเข้า NAS (แทนเลขและชื่อผู้ใช้ NAS ของคุณ):
```bash
ssh ชื่อผู้ใช้NAS@100.101.102.103 'echo NAS OK'
```
ครั้งแรกถาม fingerprint → พิมพ์ `yes` → ใส่รหัส NAS (พิมพ์รหัสแล้วจอไม่ขึ้นตัวอักษร ปกติ)

**ต้องเห็นคำว่า `NAS OK` ก่อน จึงไปขั้นต่อไป**

**ถ้าไม่เห็น NAS ในรายการ หรือ ssh ไม่ติด** = คอนเทนเนอร์ Tailscale บน NAS ไม่ได้ตั้งแบบ host
ทำให้ตัว NAS ยังไม่ได้อยู่ในเครือข่าย Tailscale จริง → ต้องแก้ก่อน **ทำครั้งเดียวจาก MacBook ที่บ้าน**:

```bash
# [พิมพ์ที่ MacBook — ครั้งเดียวเท่านั้น]
ssh ชื่อผู้ใช้NAS@192.168.1.51
# ↓ ต่อไปนี้อยู่ใน NAS แล้ว
docker inspect -f '{{.Name}} network={{.HostConfig.NetworkMode}}' $(docker ps -q)   # ดูชื่อคอนเทนเนอร์ tailscale
docker rm -f ชื่อคอนเทนเนอร์tailscale
mkdir -p /volume1/docker/tailscale
docker run -d --name tailscale --network host --restart unless-stopped \
  --cap-add NET_ADMIN --cap-add SYS_MODULE \
  -v /volume1/docker/tailscale:/var/lib/tailscale \
  -e TS_STATE_DIR=/var/lib/tailscale -e TS_HOSTNAME=ugreen-nas \
  tailscale/tailscale:latest
docker exec tailscale tailscale up        # จะพิมพ์ลิงก์ออกมา → เปิดในเบราว์เซอร์ → ล็อกอิน → อนุมัติ
docker exec tailscale tailscale ip -4     # ได้ที่อยู่ของ NAS มาใช้ในขั้นต่อไป
exit
```
เสร็จแล้วกลับไปทำขั้น 1 ที่ Mac mini อีกครั้ง — ตอนนี้ต้องเห็น NAS แล้ว

---

## ขั้น 2 — ตรวจว่าไฟล์ฐานข้อมูลอยู่ที่ไหน

**สิ่งที่ทำ:** ข้อมูลรายงานทั้งหมดอยู่ในไฟล์เดียว ต้องรู้ path ให้แน่ก่อนคัดลอก

```bash
cd /Volumes/CHUEY-Server/News_Report
grep DATABASE_URL report_center/.env
ls -lh report_center/instance/
```
**อ่านผล:**
- **ไม่เห็นบรรทัด `DATABASE_URL=`** → ฐานข้อมูลคือ `report_center/instance/report_center.db` (ค่าเริ่มต้น) ใช้คำสั่งขั้น 3 ได้เลย
- **เห็น `DATABASE_URL=sqlite:////path/ชื่อ.db`** → ใช้ path นั้นแทนในขั้น 3

---

## ขั้น 3 — ส่ง 3 ไฟล์จาก Mac mini ไป NAS โดยตรง

**สิ่งที่ทำ:** ย้ายของสำคัญ 3 ชิ้น — ข้อมูลรายงาน+บัญชีผู้ใช้ / กุญแจ Google Sheets / ค่าตั้งที่มี token LINE

```bash
cd /Volumes/CHUEY-Server/News_Report
NAS=ชื่อผู้ใช้NAS@100.101.102.103          # แก้เป็นของคุณ (จากขั้น 1)

scp report_center/instance/report_center.db $NAS:~/
scp report_center/service-account.json      $NAS:~/
scp report_center/.env                      $NAS:~/
ssh $NAS 'ls -lh ~/report_center.db ~/service-account.json ~/.env'
```
**ต้องเห็นครบทั้ง 3 ไฟล์** จากคำสั่งสุดท้าย

---

## ขั้น 4 — [ใน NAS] ดาวน์โหลดโค้ด แล้วจัดไฟล์เข้าที่

**สิ่งที่ทำ:** ดึงโค้ดระบบลง NAS และวาง 3 ไฟล์ลงตำแหน่งที่คอนเทนเนอร์จะอ่าน

เข้า NAS จาก Terminal ของ Mac mini:
```bash
ssh $NAS
```
ต่อไปนี้อยู่ใน NAS แล้ว — ดูชื่อ volume ก่อน:
```bash
ls /volume*
```
เห็นเป็น `/volume1` หรือ `/volume2` → ใส่ชื่อนั้นในบรรทัดแรกด้านล่าง:
```bash
VOL=/volume1
mkdir -p $VOL/docker && cd $VOL/docker
git clone https://github.com/chuey5910/News_Report.git news_report
cd news_report
git checkout claude/news-reporting-app-mvo1r6
mkdir -p data secrets
mv ~/report_center.db      data/
mv ~/service-account.json  secrets/
mv ~/.env                  report_center/.env
ls -lh data secrets report_center/.env
```
**ต้องเห็น:** `data/report_center.db` · `secrets/service-account.json` · `report_center/.env`

---

## ขั้น 5 — [ใน NAS] แก้ค่าตั้ง 3 บรรทัด

**สิ่งที่ทำ:** ค่าเดิมชี้ path บน Mac mini — เปลี่ยนเป็น path ในคอนเทนเนอร์ และตั้งลิงก์ที่จะไปโผล่ในไลน์

แทน `100.101.102.103` ด้วยที่อยู่ Tailscale ของ NAS:
```bash
sed -i '/^DATABASE_URL=/d;/^GOOGLE_SHEETS_CREDENTIALS_FILE=/d;/^REPORT_CENTER_BASE_URL=/d' report_center/.env
cat >> report_center/.env <<'EOF'

DATABASE_URL=sqlite:////data/report_center.db
GOOGLE_SHEETS_CREDENTIALS_FILE=secrets/service-account.json
EOF
echo 'REPORT_CENTER_BASE_URL=http://100.101.102.103:5001' >> report_center/.env
grep -E '^(DATABASE_URL|GOOGLE_SHEETS_CREDENTIALS_FILE|REPORT_CENTER_BASE_URL)=' report_center/.env
```
**ต้องเห็น 3 บรรทัดนี้** (บรรทัดที่ 3 เป็นเลขของคุณ):
```
DATABASE_URL=sqlite:////data/report_center.db
GOOGLE_SHEETS_CREDENTIALS_FILE=secrets/service-account.json
REPORT_CENTER_BASE_URL=http://100.101.102.103:5001
```

---

## ขั้น 6 — [ใน NAS] เปิดระบบ

**สิ่งที่ทำ:** สร้างและเปิด 2 คอนเทนเนอร์ — `web` (หน้าเว็บ) และ `scheduler` (แจ้งเตือนไลน์)
ครั้งแรกใช้เวลา 2-5 นาที เพราะต้องติดตั้งส่วนประกอบ

```bash
docker compose up -d --build
docker compose ps
curl -s -o /dev/null -w 'เว็บตอบรหัส %{http_code}\n' http://127.0.0.1:5001/
docker compose exec web flask --app report_center list-users
```
**ต้องเห็น:** ทั้ง 2 คอนเทนเนอร์สถานะ `Up` · `เว็บตอบรหัส 302` · รายชื่อผู้ใช้เดิมครบ

**ถ้าติด:**
| อาการ | ทำอะไร |
|---|---|
| `permission denied` | เติม `sudo` หน้าคำสั่ง `docker` ทุกคำสั่ง |
| `docker compose: command not found` | ใช้ `docker-compose` (มีขีดกลาง) แทนทุกจุด |
| คอนเทนเนอร์ไม่ขึ้น `Up` | ดูสาเหตุ: `docker compose logs web \| tail -30` |
| `list-users` ไม่มีรายชื่อ | ฐานข้อมูลไม่ได้ถูกวางถูกที่ — กลับไปตรวจขั้น 4-5 |

---

## ขั้น 7 — ทดสอบจากมือถือ

**สิ่งที่ทำ:** พิสูจน์ว่าใช้งานได้จริง ก่อนปิดระบบเดิม

1. เปิดสวิตช์ **Tailscale** บนมือถือ
2. เปิด Safari ไปที่ `http://100.101.102.103:5001` (พิมพ์ `http://` ให้ครบ)
3. ล็อกอินด้วยบัญชีเดิม → ต้องเห็นรายงานเก่าครบ
4. บันทึกรายงานใหม่ 1 รายการ → ตรวจว่าขึ้นแถวใหม่ใน Google Sheet
5. ทดสอบแจ้งเตือนไลน์ `[ใน NAS]`:
   ```bash
   docker compose exec web flask --app report_center line-status
   docker compose exec web flask --app report_center line-daily
   ```
   ต้องขึ้นโหมด "เข้าเป้าหมาย (กลุ่ม)" และมีข้อความเข้ากลุ่มไลน์จริง
   *(ถ้าขึ้น 429 = โควตาเดือนนั้นหมด ไม่เกี่ยวกับการย้าย)*
6. ทดสอบว่าเปิดเองได้หลังไฟดับ `[ใน NAS]`: `sudo reboot` → รอ 3 นาที → เข้าเว็บใหม่ต้องได้เลยโดยไม่ต้องสั่งอะไร

---

## ขั้น 8 — ปิดระบบเดิมบน Mac mini

**สิ่งที่ทำ:** หยุดของเก่า ไม่ให้แจ้งเตือนไลน์ส่งซ้ำจาก 2 เครื่อง — **ยังไม่ลบข้อมูล**

ทำหลังผ่านขั้น 7 ครบทุกข้อ (พิมพ์ใน Terminal ของ Mac mini, ออกจาก ssh ของ NAS ด้วย `exit` ก่อน):
```bash
crontab -l > ~/crontab-backup.txt     # สำรองตารางเดิมไว้ก่อน
crontab -r                             # ปิดงานแจ้งเตือน
launchctl unload ~/Library/LaunchAgents/com.chuey.reportcenter.plist    # ปิดเว็บ
```

**เก็บ Mac mini ไว้เฉยๆ อีก 2-4 สัปดาห์** ยังไม่ลบไฟล์ ถ้า NAS มีปัญหา กลับไปเปิดใช้ได้ทันที:
```bash
launchctl load ~/Library/LaunchAgents/com.chuey.reportcenter.plist
crontab ~/crontab-backup.txt
```

---

## ขั้น 9 — แจ้งพนักงาน

URL เปลี่ยนเป็นของ NAS — ต้องทำ 2 อย่างต่อคน:
1. **แชร์เครื่อง NAS ให้เขา**: login.tailscale.com/admin/machines → เครื่อง NAS → ⋯ → **Share...** → ส่งลิงก์ให้เจ้าตัวทางแชทส่วนตัว
2. บอกให้ลบไอคอนเดิมบนหน้าจอมือถือ แล้วเปิด URL ใหม่ → Share → **เพิ่มไปยังโฮมสกรีน**

---

## คำสั่งดูแลประจำ (พิมพ์ใน NAS)

```bash
cd /volume1/docker/news_report

docker compose ps                   # สถานะ
docker compose logs -f web          # log หน้าเว็บ
docker compose logs -f scheduler    # log แจ้งเตือนไลน์
docker compose restart              # รีสตาร์ท
git pull && docker compose up -d --build                   # อัปเดตเวอร์ชันใหม่
cp data/report_center.db data/backup-$(date +%Y%m%d).db    # สำรองฐานข้อมูล
```

**เข้า NAS จากที่ทำงานได้เสมอด้วย** (พิมพ์ที่ Mac mini): `ssh ชื่อผู้ใช้NAS@100.101.102.103`
