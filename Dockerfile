FROM python:3.12-slim

# TZ สำคัญสำหรับคอนเทนเนอร์ scheduler — cron ยิงงานตามเวลาของระบบ
# (โค้ดแอปคำนวณเวลาไทยเป็น UTC+7 เองอยู่แล้ว ไม่ขึ้นกับค่านี้)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Bangkok

RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata cron curl \
    && ln -snf "/usr/share/zoneinfo/$TZ" /etc/localtime && echo "$TZ" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ติดตั้ง dependency ก่อนคัดลอกโค้ด — แก้โค้ดแล้ว build ใหม่จะเร็วเพราะใช้ cache ชั้นนี้ซ้ำ
COPY report_center/requirements.txt /app/report_center/requirements.txt
RUN pip install --no-cache-dir -r /app/report_center/requirements.txt gunicorn==23.0.0

COPY . /app
RUN chmod +x /app/docker/scheduler-entrypoint.sh

EXPOSE 5001

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5001", "report_center.wsgi:application"]
