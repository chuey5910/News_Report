#!/bin/sh
# ตรวจสุขภาพระบบบน NAS ด้วยคำสั่งเดียว — ใช้หลังเปลี่ยนผู้ให้บริการเน็ต ไฟดับ ย้ายเราเตอร์
# หรือเมื่อใดก็ตามที่สงสัยว่าระบบยังดีอยู่ไหม
#
# วิธีใช้ (บน NAS): sudo sh /volume1/docker/news_report/app/docker/nas-check.sh
set -u
APP_DIR="${APP_DIR:-/volume1/docker/news_report/app}"
DATA_DIR="${DATA_DIR:-/volume1/docker/news_report/data}"
fail=0

say() { printf '%s\n' "$1"; }
ok()   { say "  [ ผ่าน ] $1"; }
bad()  { say "  [ ไม่ผ่าน ] $1"; fail=$((fail + 1)); }

say "===== ตรวจระบบรายงานข่าวบน NAS ====="
say ""

say "1. คอนเทนเนอร์"
for name in news-report-web news-report-scheduler; do
    state=$(docker inspect -f '{{.State.Status}}' "$name" 2>/dev/null || echo "ไม่พบ")
    if [ "$state" = "running" ]; then ok "$name กำลังทำงาน"
    else bad "$name สถานะ: $state  (สั่งเปิด: cd $APP_DIR && sudo docker compose up -d)"; fi
done

say ""
say "2. หน้าเว็บ"
code=$(curl -s -m 10 -o /dev/null -w '%{http_code}' http://127.0.0.1:5001/ 2>/dev/null || echo 000)
if [ "$code" = "302" ] || [ "$code" = "200" ]; then ok "เว็บตอบรหัส $code"
else bad "เว็บไม่ตอบ (รหัส $code)  (ดูสาเหตุ: cd $APP_DIR && sudo docker compose logs --tail 30 web)"; fi

say ""
say "3. Tailscale (ทางเข้าจากมือถือ)"
ts=$(docker ps --format '{{.Names}}' | grep -i tailscale | head -1)
if [ -n "$ts" ]; then
    ip=$(docker exec "$ts" tailscale ip -4 2>/dev/null | head -1)
    if [ -n "$ip" ]; then
        ok "ออนไลน์ — ลิงก์ใช้งาน: http://$ip:5001"
    else
        bad "คอนเทนเนอร์ $ts ทำงานแต่ยังไม่ได้ต่อเข้าเครือข่าย  (สั่งต่อใหม่: sudo docker exec $ts tailscale up)"
    fi
else
    bad "ไม่พบคอนเทนเนอร์ tailscale"
fi

say ""
say "4. ฐานข้อมูลและไฟล์สำรอง"
if [ -f "$DATA_DIR/report_center.db" ]; then
    size=$(du -h "$DATA_DIR/report_center.db" | cut -f1)
    ok "ฐานข้อมูลอยู่ครบ ($size)"
else
    bad "ไม่พบฐานข้อมูลที่ $DATA_DIR/report_center.db"
fi
last=$(ls -t "$DATA_DIR/backup"/report_center-*.db 2>/dev/null | head -1)
if [ -n "$last" ]; then
    count=$(ls "$DATA_DIR/backup"/report_center-*.db 2>/dev/null | wc -l | tr -d ' ')
    ok "สำรองล่าสุด $(basename "$last") (เก็บไว้ $count ไฟล์)"
else
    bad "ยังไม่มีไฟล์สำรอง  (สั่งสำรองเดี๋ยวนี้: cd $APP_DIR && sudo docker compose exec -T web flask --app report_center backup-db)"
fi

say ""
say "5. แจ้งเตือน LINE"
(cd "$APP_DIR" && docker compose exec -T web flask --app report_center line-status 2>/dev/null) | sed 's/^/  /' \
    || bad "เรียกดูสถานะ LINE ไม่ได้"

say ""
if [ "$fail" -eq 0 ]; then
    say "===== ระบบปกติทุกข้อ ====="
else
    say "===== มีปัญหา $fail ข้อ ดูวิธีแก้ในวงเล็บของข้อที่ไม่ผ่าน ====="
fi
exit "$fail"
