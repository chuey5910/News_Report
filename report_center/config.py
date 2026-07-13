import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _load_dotenv():
    """Load a .env file (repo root or report_center/) before Config reads env vars,
    so deployments can configure everything by editing one file. Best-effort."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for candidate in (os.path.join(BASE_DIR, "..", ".env"), os.path.join(BASE_DIR, ".env")):
        if os.path.exists(candidate):
            load_dotenv(candidate, override=False)


_load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "instance", "report_center.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # API key required by external systems (e.g. the RSS news_report pipeline)
    # to pull report data for notification purposes. Set via environment
    # variable in production; never commit real keys.
    API_KEY = os.environ.get("REPORT_CENTER_API_KEY", "dev-api-key-change-me")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # ตั้ง SESSION_COOKIE_SECURE=1 เมื่อรันหลัง HTTPS (แนะนำสำหรับใช้งานจริง)
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"

    # ป้องกัน brute-force: ล็อกการล็อกอินชั่วคราวเมื่อกรอกผิดหลายครั้งติดกัน
    LOGIN_MAX_FAILED_ATTEMPTS = int(os.environ.get("LOGIN_MAX_FAILED_ATTEMPTS", "5"))
    LOGIN_LOCKOUT_MINUTES = int(os.environ.get("LOGIN_LOCKOUT_MINUTES", "15"))

    # --- Google Sheets auto-sync (optional) ---
    # เมื่อบันทึกรายงานใหม่ ระบบจะ sync ลง Google Sheet ให้อัตโนมัติ เพื่อให้เว็บอื่นดึงไปแสดงได้
    # ตั้งค่า credentials ได้ 2 แบบ (เลือกอย่างใดอย่างหนึ่ง):
    #   1) GOOGLE_SHEETS_CREDENTIALS_FILE = path ไปยังไฟล์ service-account JSON
    #   2) GOOGLE_SHEETS_CREDENTIALS_JSON = เนื้อหา JSON ของ service account (ใส่ตรงๆ)
    # ถ้าไม่ตั้งค่า SPREADSHEET_ID ระบบจะข้ามการ sync ไปเงียบๆ (ไม่ทำให้การบันทึกล้มเหลว)
    GOOGLE_SHEETS_CREDENTIALS_FILE = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_FILE", "")
    GOOGLE_SHEETS_CREDENTIALS_JSON = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_JSON", "")
    GOOGLE_SHEETS_SPREADSHEET_ID = os.environ.get("GOOGLE_SHEETS_SPREADSHEET_ID", "")
    GOOGLE_SHEETS_WORKSHEET = os.environ.get("GOOGLE_SHEETS_WORKSHEET", "reports")
