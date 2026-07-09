import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


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
