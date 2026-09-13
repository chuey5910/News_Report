#!/bin/sh
# ติดตั้งตารางเวลา แล้วรัน cron ไว้เบื้องหน้า เพื่อให้ Docker คุมการรีสตาร์ทเอง
set -e
crontab /app/docker/crontab
echo "scheduler พร้อมทำงาน — เวลาในคอนเทนเนอร์: $(date '+%Y-%m-%d %H:%M:%S %Z')"
crontab -l | grep -v '^#' | grep -v '^$' | sed 's/^/  ตาราง: /'
exec cron -f
