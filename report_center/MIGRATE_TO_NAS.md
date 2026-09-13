# ย้ายระบบจาก Mac mini ไป NAS — ทำตามลำดับครั้งเดียวจบ

ค่าประจำเครื่องที่ใช้ในคู่มือนี้ (แก้ตรงนี้ถ้าเปลี่ยน):

| อะไร | ค่า |
|---|---|
| NAS ในบ้าน | `192.168.1.51` |
| Mac mini ผ่าน Tailscale | `100.82.97.85` (ผู้ใช้ `adisakromchampa`) |
| โฟลเดอร์ระบบเดิมบน Mac mini | `/Volumes/CHUEY-Server/News_Report` |

**แต่ละขั้นบอกไว้ว่าพิมพ์ที่เครื่องไหน** — ทุกคำสั่งพิมพ์ใน **Terminal บน MacBook** ยกเว้นที่ระบุว่า
`[ใน NAS]` ซึ่งหมายถึงหลังจาก ssh เข้า NAS แล้ว (หน้าต่างเดิมนั้น)

---

## ขั้น 0 — เตรียม (ครั้งเดียว)

**สิ่งที่ทำ:** เปิดช่องทางให้ MacBook สั่งงาน Mac mini และ NAS ได้จากบรรทัดคำสั่ง

1. **บน Mac mini** (รีโมทเข้าไปทำ): System Settings → General → **Sharing** → เปิด **Remote Login**
2. **บน NAS** (หน้าเว็บ UGOS): ตั้งค่า → **Terminal & SNMP** → เปิด **SSH**

ทดสอบว่าเข้าได้ทั้งสองเครื่อง:
```bash
ssh adisakromchampa@100.82.97.85 'echo Mac mini OK'
ssh ชื่อผู้ใช้NAS@192.168.1.51 'echo NAS OK'
```
> ครั้งแรกจะถาม fingerprint ให้พิมพ์ `yes` แล้วใส่รหัสของเครื่องนั้น (พิมพ์รหัสแล้วจอไม่ขึ้นตัวอักษร — ปกติ)
> ต้องเห็นข้อความ `Mac mini OK` และ `NAS OK` ก่อน จึงไปขั้นต่อไป

---

## ขั้น 1 — หาว่าไฟล์ฐานข้อมูลจริงอยู่ที่ไหน

**สิ่งที่ทำ:** ระบบเก็บข้อมูลเป็นไฟล์เดียว ต้องรู้ path ให้แน่ก่อนคัดลอก

```bash
ssh adisakromchampa@100.82.97.85 'cd /Volumes/CHUEY-Server/News_Report && grep DATABASE_URL report_center/.env; ls -la report_center/instance/'
```
**อ่านผลอย่างนี้:**
- ถ้า **ไม่เห็นบรรทัด** `DATABASE_URL=` → ฐานข้อมูลคือไฟล์ `report_center.db` ในโฟลเดอร์ `instance/` ที่แสดงอยู่ (ใช้ค่าเริ่มต้น) — ใช้คำสั่งขั้น 2 ได้เลย
- ถ้า **เห็น** `DATABASE_URL=sqlite:////path/ชื่อไฟล์.db` → ให้ใช้ path นั้นแทนในขั้น 2

---

## ขั้น 2 — ดึง 3 ไฟล์จาก Mac mini มาพักไว้บน MacBook

**สิ่งที่ทำ:** ย้ายของสำคัญ 3 ชิ้น = ข้อมูลรายงานทั้งหมด + กุญแจ Google Sheets + ค่าตั้งระบบ (token LINE ฯลฯ)

```bash
mkdir -p ~/nas-migrate && cd ~/nas-migrate
M=adisakromchampa@100.82.97.85:/Volumes/CHUEY-Server/News_Report/report_center
scp $M/instance/report_center.db .
scp $M/service-account.json .
scp $M/.env .
ls -lh
```
**ต้องเห็นครบ 3 ไฟล์:** `report_center.db`, `service-account.json`, `.env`
> ไฟล์ `.env` มี token จริง — เก็บไว้ในเครื่อง อย่าส่งให้ใคร และลบโฟลเดอร์นี้ทิ้งเมื่อย้ายเสร็จ

---

## ขั้น 3 — ส่ง 3 ไฟล์เข้า NAS

**สิ่งที่ทำ:** วางไฟล์ไว้ในบ้านของผู้ใช้บน NAS ก่อน แล้วขั้นต่อไปจะจัดเข้าที่

```bash
cd ~/nas-migrate
scp report_center.db service-account.json .env ชื่อผู้ใช้NAS@192.168.1.51:~/
```

---

## ขั้น 4 — [ใน NAS] ดาวน์โหลดโค้ดและจัดไฟล์เข้าที่

**สิ่งที่ทำ:** ดึงโค้ดระบบลง NAS แล้ววางฐานข้อมูล/กุญแจ/ค่าตั้ง ลงตำแหน่งที่คอนเทนเนอร์จะอ่าน

เข้า NAS ก่อน:
```bash
ssh ชื่อผู้ใช้NAS@192.168.1.51
```

จากนั้น (อยู่ใน NAS แล้ว) ดูชื่อ volume ว่าเป็นอะไร:
```bash
ls /volume*
```
เห็นเป็น `/volume1` หรือ `/volume2` — ใช้ชื่อนั้นในบรรทัดถัดไป (ตัวอย่างใช้ `/volume1`):
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
**ต้องเห็น:** `data/report_center.db`, `secrets/service-account.json`, `report_center/.env`

---

## ขั้น 5 — [ใน NAS] แก้ค่าตั้ง 2 บรรทัด

**สิ่งที่ทำ:** ค่าเดิมชี้ไปที่ path บน Mac mini ต้องเปลี่ยนเป็น path ในคอนเทนเนอร์

```bash
sed -i '/^DATABASE_URL=/d;/^GOOGLE_SHEETS_CREDENTIALS_FILE=/d' report_center/.env
printf '\nDATABASE_URL=sqlite:////data/report_center.db\nGOOGLE_SHEETS_CREDENTIALS_FILE=secrets/service-account.json\n' >> report_center/.env
grep -E '^(DATABASE_URL|GOOGLE_SHEETS_CREDENTIALS_FILE)=' report_center/.env
```
**ต้องเห็น 2 บรรทัดนี้เป๊ะ:**
```
DATABASE_URL=sqlite:////data/report_center.db
GOOGLE_SHEETS_CREDENTIALS_FILE=secrets/service-account.json
```

---

## ขั้น 6 — [ใน NAS] เปิดระบบ

**สิ่งที่ทำ:** สร้างและเปิด 2 คอนเทนเนอร์ (เว็บ + ตัวแจ้งเตือน LINE) ครั้งแรกใช้เวลา 2-5 นาที

```bash
docker compose up -d --build
docker compose ps
curl -s -o /dev/null -w 'เว็บตอบรหัส %{http_code}\n' http://127.0.0.1:5001/
docker compose exec web flask --app report_center list-users
```
**ต้องเห็น:** ทั้ง 2 คอนเทนเนอร์สถานะ `Up` / `เว็บตอบรหัส 302` / รายชื่อผู้ใช้เดิมครบ

**ถ้าติด:**
- `permission denied` → เติม `sudo` หน้าคำสั่ง `docker` ทุกคำสั่ง
- `docker compose: command not found` → ใช้ `docker-compose` (มีขีดกลาง) แทนทุกจุด
- คอนเทนเนอร์ไม่ขึ้น `Up` → ดูสาเหตุด้วย `docker compose logs web | tail -30`

---

## ขั้น 7 — [ใน NAS] ทำให้เข้าถึงผ่าน Tailscale ได้

**สิ่งที่ทำ:** เว็บเปิดพอร์ต 5001 อยู่ที่ตัว NAS แล้ว เหลือให้ Tailscale พา NAS ออกไปให้มือถือเห็น

เช็คว่าคอนเทนเนอร์ Tailscale ตั้งโหมดเครือข่ายแบบไหน:
```bash
docker inspect -f '{{.Name}}  network={{.HostConfig.NetworkMode}}' $(docker ps -q)
```

### กรณี ก — บรรทัดของ tailscale ขึ้น `network=host` (ที่ต้องการ)
ใช้ได้เลย หาที่อยู่ของ NAS ในเครือข่าย Tailscale:
```bash
docker exec ชื่อคอนเทนเนอร์tailscale tailscale ip -4
```

### กรณี ข — ขึ้นเป็น `bridge` หรืออย่างอื่น (มือถือจะเข้าเว็บไม่ได้ ต้องแก้)
สร้างใหม่แบบ host mode (แทน `ชื่อคอนเทนเนอร์tailscale` ด้วยชื่อที่เห็นจากคำสั่งข้างบน):
```bash
docker rm -f ชื่อคอนเทนเนอร์tailscale
mkdir -p $VOL/docker/tailscale
docker run -d --name tailscale --network host --restart unless-stopped \
  --cap-add NET_ADMIN --cap-add SYS_MODULE \
  -v $VOL/docker/tailscale:/var/lib/tailscale \
  -e TS_STATE_DIR=/var/lib/tailscale -e TS_HOSTNAME=ugreen-nas \
  tailscale/tailscale:latest
docker exec tailscale tailscale up
```
คำสั่งสุดท้ายจะพิมพ์ **ลิงก์** ออกมา — copy ไปเปิดในเบราว์เซอร์ ล็อกอินบัญชี Tailscale แล้วกดอนุมัติ
จากนั้นดูที่อยู่ด้วย `docker exec tailscale tailscale ip -4`

### ตั้งที่อยู่นี้ลงค่าตั้ง (ทำทั้งสองกรณี)
แทน `100.x.y.z` ด้วยเลขที่ได้จากคำสั่ง `tailscale ip -4`:
```bash
cd $VOL/docker/news_report
sed -i '/^REPORT_CENTER_BASE_URL=/d' report_center/.env
echo 'REPORT_CENTER_BASE_URL=http://100.x.y.z:5001' >> report_center/.env
docker compose restart
```
> ค่านี้คือลิงก์ที่ไปปรากฏในข้อความแจ้งเตือนไลน์ ถ้าไม่ตั้งให้ถูก ลิงก์ในไลน์จะกดไม่ได้

---

## ขั้น 8 — ทดสอบจากมือถือ

**สิ่งที่ทำ:** พิสูจน์ว่าใช้งานได้จริงก่อนปิดระบบเดิม

1. เปิดสวิตช์ **Tailscale** บนมือถือ
2. เปิด Safari ไปที่ `http://100.x.y.z:5001` (เลขจากขั้น 7 — ต้องพิมพ์ `http://` ให้ครบ)
3. ล็อกอินด้วยบัญชีเดิม → ต้องเห็นรายงานเก่าครบ
4. บันทึกรายงานใหม่ 1 รายการ → ตรวจว่าขึ้นแถวใหม่ใน Google Sheet ด้วย
5. **ทดสอบแจ้งเตือนไลน์** [ใน NAS]:
   ```bash
   docker compose exec web flask --app report_center line-status
   docker compose exec web flask --app report_center line-daily
   ```
   ต้องขึ้นโหมดส่ง "เข้าเป้าหมาย (กลุ่ม)" และมีข้อความเข้ากลุ่มไลน์จริง
   *(ถ้าขึ้น 429 = โควตาเดือนนั้นหมด ไม่ใช่ความผิดของการย้าย)*
6. **ทดสอบว่าเปิดเองได้หลังไฟดับ** [ใน NAS]: สั่งรีบูต `sudo reboot` รอ 3 นาที แล้วเข้าเว็บใหม่ — ต้องขึ้นเองโดยไม่ต้องสั่งอะไร

---

## ขั้น 9 — ปิดระบบเดิมบน Mac mini

**สิ่งที่ทำ:** หยุดของเก่าเพื่อไม่ให้แจ้งเตือนไลน์ส่งซ้ำ 2 เครื่อง (แต่**ยังไม่ลบข้อมูล** เก็บเป็นสำรอง)

ทำหลังผ่านขั้น 8 ครบทุกข้อแล้วเท่านั้น:
```bash
ssh adisakromchampa@100.82.97.85
crontab -l > ~/crontab-backup.txt        # สำรองตารางเดิมไว้ก่อน
crontab -r                                # ลบงานแจ้งเตือน
launchctl unload ~/Library/LaunchAgents/com.chuey.reportcenter.plist   # ปิดเว็บ
exit
```

**เก็บ Mac mini ไว้เฉยๆ อีก 2-4 สัปดาห์** ยังไม่ต้องลบไฟล์ ถ้า NAS มีปัญหาจะกลับไปเปิดใช้ได้ทันทีด้วย:
```bash
launchctl load ~/Library/LaunchAgents/com.chuey.reportcenter.plist
crontab ~/crontab-backup.txt
```

**เก็บกวาดบน MacBook** (ลบไฟล์ความลับที่พักไว้):
```bash
rm -rf ~/nas-migrate
```

---

## ขั้น 10 — แจ้งพนักงาน

URL เปลี่ยนเป็น `http://100.x.y.z:5001` (ของ NAS) — ต้องทำ 2 อย่างต่อคน:
1. **แชร์เครื่อง NAS ให้เขาใน Tailscale**: login.tailscale.com/admin/machines → เครื่อง NAS → ⋯ → **Share...** → ส่งลิงก์ให้เจ้าตัว
2. บอกให้ลบไอคอนเดิมบนหน้าจอมือถือ แล้วเปิด URL ใหม่ → Share → **เพิ่มไปยังโฮมสกรีน**

---

## คำสั่งดูแลประจำ (ใช้ใน NAS)

```bash
cd /volume1/docker/news_report

docker compose ps                   # สถานะ
docker compose logs -f web          # log หน้าเว็บ
docker compose logs -f scheduler    # log แจ้งเตือน LINE
docker compose restart              # รีสตาร์ท
git pull && docker compose up -d --build        # อัปเดตเวอร์ชันใหม่
cp data/report_center.db data/backup-$(date +%Y%m%d).db   # สำรองฐานข้อมูล
```
