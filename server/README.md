# CHUEY-Server — ส่งข่าวเข้ากลุ่ม LINE

บริการเสริมสำหรับ **push ข่าวเข้ากลุ่มแชท LINE** (นอกเหนือจาก Broadcast ที่ส่งถึงเพื่อนของ OA
รายคน) รันแยกบน CHUEY-Server เพราะการส่งเข้ากลุ่มต้องใช้ Push API แบบระบุ `groupId` และ
`groupId` จะรู้ได้ก็ต่อเมื่อมี webhook คอยดักตอน OA เข้ากลุ่ม — ซึ่ง GitHub Pages (static) ทำไม่ได้

- `chuey_line_server.py` — ตัวบริการ (Python 3 stdlib ล้วน ไม่ต้อง pip install)
- `chuey-line-relay.service` — systemd unit ตัวอย่าง
- `chuey-line-relay.env.example` — ตัวอย่างไฟล์ตั้งค่า (ความลับ)

## บริการทำอะไร (3 endpoint)

| Endpoint | ใคร่เรียก | หน้าที่ |
|---|---|---|
| `POST /line/webhook` | LINE Platform | รับ event, ตรวจลายเซ็น, เก็บ/ลบ `groupId` ลง `groups.json` |
| `POST /notify` | pipeline (GitHub Actions) | รับ message + bearer token แล้ว push ไปทุกกลุ่มที่เก็บไว้ |
| `GET /health` | คุณ/monitoring | ตอบ 200 พร้อมจำนวนกลุ่มที่ลงทะเบียน |

## ข้อกำหนดเบื้องต้น (สำคัญ)

1. **CHUEY-Server ต้องเข้าถึงได้จากอินเทอร์เน็ต (public)** และมี **HTTPS + โดเมน** — LINE บังคับ
   ว่า webhook URL ต้องเป็น `https://` ที่มีใบรับรองใช้งานได้จริง (แนะนำตั้ง reverse proxy เช่น
   Caddy/Nginx + Let's Encrypt ชี้มาที่พอร์ตของบริการ)
2. เปิดสิทธิ์ให้ OA เข้ากลุ่มได้ที่ **LINE Official Account Manager → ตั้งค่า → อนุญาตให้เข้าร่วม
   แชทกลุ่ม** (ค่าเริ่มต้นปิดอยู่ ทำให้ OA เด้งออกจากกลุ่มเอง)

## ติดตั้งบน CHUEY-Server

```bash
# 1) วางไฟล์
sudo mkdir -p /opt/chuey-line-relay
sudo cp chuey_line_server.py /opt/chuey-line-relay/

# 2) ตั้งค่าลับ
sudo cp chuey-line-relay.env.example /etc/chuey-line-relay.env
sudo nano /etc/chuey-line-relay.env      # เติม LINE_CHANNEL_SECRET / TOKEN / CHUEY_SERVER_TOKEN
sudo chmod 600 /etc/chuey-line-relay.env

# 3) รันเป็น service
sudo cp chuey-line-relay.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now chuey-line-relay
sudo systemctl status chuey-line-relay          # ควรเห็น active (running)
curl -s http://127.0.0.1:8080/health            # {"status":"ok","groups":0}
```

จากนั้นตั้ง reverse proxy ให้ `https://<โดเมนของคุณ>` ชี้มาที่ `127.0.0.1:8080`
(ตัวอย่าง Caddy: `<โดเมน> { reverse_proxy 127.0.0.1:8080 }` — จัดการ HTTPS ให้อัตโนมัติ)

## ตั้งค่า webhook ฝั่ง LINE

LINE Developers Console → channel ของ OA "KhuFah" → **Messaging API**:
- **Webhook URL** = `https://<โดเมนของคุณ>/line/webhook` → กด **Verify** (ต้องได้ Success)
- เปิด **Use webhook** = ON

## เชื่อมกับ pipeline หลัก

ที่ GitHub repo `chuey5910/News_Report` → **Settings → Secrets and variables → Actions**:
- **Variables** → `CHUEY_SERVER_NOTIFY_URL` = `https://<โดเมนของคุณ>/notify`
- **Secrets** → `CHUEY_SERVER_TOKEN` = ค่าเดียวกับใน `/etc/chuey-line-relay.env`

ถ้าไม่ตั้งสองค่านี้ pipeline จะข้ามการส่งกลุ่มไปเงียบๆ (Broadcast + เว็บยังทำงานปกติ)

## วิธีใช้งานประจำวัน

1. เชิญ OA "KhuFah" เข้ากลุ่มที่ต้องการ (หรือให้ OA อยู่ในกลุ่มแล้วมีคนพิมพ์อะไรสักข้อความ) →
   บริการจะบันทึก `groupId` อัตโนมัติ ตรวจได้ที่ `GET /health` (จำนวนกลุ่มจะเพิ่มขึ้น)
2. รอบข่าวถัดไป (07:05 / 16:05 น.) ระบบจะ push ข่าวเข้าทุกกลุ่มที่ลงทะเบียนไว้เอง
3. เตะ OA ออกจากกลุ่ม → บริการลบ `groupId` นั้นออกให้อัตโนมัติ (event `leave`)

## ทดสอบเร็วๆ

```bash
# ทดสอบ push โดยไม่ต้องรอรอบข่าว (ต้องมีอย่างน้อย 1 กลุ่มลงทะเบียนแล้ว)
curl -X POST https://<โดเมน>/notify \
  -H "Authorization: Bearer <CHUEY_SERVER_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"type":"text","text":"ทดสอบส่งเข้ากลุ่มจาก CHUEY-Server"}]}'
# ตอบ {"ok":true,"pushed":N,"failed":0}
```
