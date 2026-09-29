#!/bin/sh
# อัปเดตระบบบน NAS โดยดึงโค้ดจาก GitHub เองโดยตรง — ไม่ต้องผ่าน Mac mini และไม่ต้องมี git บน NAS
#
# วิธีใช้ (บน NAS):  sh /volume1/docker/news_report/app/docker/update-from-github.sh
# ระบุสาขาอื่นได้:   sh .../update-from-github.sh main
set -eu

BRANCH="${1:-claude/news-reporting-app-mvo1r6}"
APP_DIR="${APP_DIR:-/volume1/docker/news_report/app}"
REPO="${REPO:-chuey5910/News_Report}"
URL="https://codeload.github.com/$REPO/tar.gz/refs/heads/$BRANCH"

# docker บน NAS ส่วนใหญ่ต้องใช้ sudo — ตรวจให้เองว่าต้องเติมไหม
DOCKER="docker"
if ! docker info >/dev/null 2>&1; then
    DOCKER="sudo docker"
fi

if [ ! -f "$APP_DIR/docker-compose.yml" ]; then
    echo "ไม่พบระบบที่ $APP_DIR — ตรวจ path หรือกำหนด APP_DIR ให้ถูกต้อง" >&2
    exit 1
fi

echo "1/3 ดึงโค้ดล่าสุดจาก GitHub (สาขา $BRANCH)"
# เอาเฉพาะไฟล์ของระบบรายงานข่าว ไม่ลากโปรเจกต์อื่นในคลังเดียวกันมาด้วย
# ไฟล์ .env และฐานข้อมูลอยู่นอกโฟลเดอร์นี้ จึงไม่ถูกทับ
curl -fsSL "$URL" | tar xz --strip-components=1 -C "$APP_DIR" --wildcards \
    '*/report_center/*' '*/Dockerfile' '*/docker-compose.yml' '*/.dockerignore' '*/docker/*'

echo "2/3 สร้างและรีสตาร์ทคอนเทนเนอร์"
cd "$APP_DIR"
$DOCKER compose up -d --build

echo "3/3 ตรวจผล"
$DOCKER compose ps
curl -s -m 10 -o /dev/null -w 'เว็บตอบรหัส %{http_code} (302 = ปกติ)\n' http://127.0.0.1:5001/
echo "อัปเดตเสร็จแล้ว"
