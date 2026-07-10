"""Sync each saved report into a Google Sheet so another website can read it.

Design goals:
- **Never break a save.** Every entry point is wrapped so any failure (not
  configured, network blocked, auth error, quota) is logged and swallowed —
  the report is already safely in SQLite regardless.
- **Optional.** If GOOGLE_SHEETS_SPREADSHEET_ID (or credentials) is not set,
  syncing is skipped silently, mirroring how the original news_report project
  treats an unset LINE token.
- **Flat, consumer-friendly rows.** One row per report; leaders and vehicles
  (which live in child tables) are flattened into single text cells so the
  downstream display website only has to read one tab.
- **Upsert by id.** Re-syncing an existing report updates its row instead of
  appending a duplicate, so this also works if editing is added later.
"""

import json
import logging

from .models import REPORT_TYPE_LABELS

logger = logging.getLogger(__name__)

# Column order for the Google Sheet. Keep in sync with the header written by
# _ensure_header(). The consumer website should key off these column names.
HEADER = [
    "id",
    "report_type",
    "report_type_label",
    "title",
    "activity_types",
    "problem_group_types",
    "event_datetime",
    "event_end_datetime",
    "permit_status",
    "permit_location",
    "permit_duration_days",
    "group_name",
    "location",
    "mass_count",
    "activity_format",
    "demands",
    "supporters",
    "affiliations",
    "overnight_equipment_status",
    "overnight_equipment_detail",
    "vehicle_status",
    "leaders",
    "vehicles",
    "other_info",
    "trend_assessment",
    "reporter_name",
    "reporter_phone",
    "created_by",
    "created_at",
]


def _fmt_dt(value):
    return value.strftime("%Y-%m-%d %H:%M") if value else ""


def report_to_row(report):
    """Flatten a NewsReport (and its child rows) into a single sheet row."""
    leaders = "; ".join(leader.full_name for leader in report.leaders)
    vehicles = " | ".join(
        "/".join(filter(None, [v.vehicle_type, v.plate_number, v.province, v.color]))
        for v in report.vehicles
    )
    return [
        report.id,
        report.report_type,
        REPORT_TYPE_LABELS.get(report.report_type, report.report_type),
        report.title,
        report.activity_types or "",
        report.problem_group_types or "",
        _fmt_dt(report.event_datetime),
        _fmt_dt(report.event_end_datetime),
        report.permit_status or "",
        report.permit_location or "",
        report.permit_duration_days if report.permit_duration_days is not None else "",
        report.group_name or "",
        report.location or "",
        report.mass_count or "",
        report.activity_format or "",
        report.demands or "",
        report.supporters or "",
        report.affiliations or "",
        report.overnight_equipment_status or "",
        report.overnight_equipment_detail or "",
        report.vehicle_status or "",
        leaders,
        vehicles,
        report.other_info or "",
        report.trend_assessment or "",
        report.reporter_name or "",
        report.reporter_phone or "",
        report.created_by.full_name if report.created_by else "",
        _fmt_dt(report.created_at),
    ]


def _load_credentials(config):
    """Build a gspread client from either an inline JSON string or a file path.
    Returns None if nothing is configured."""
    from google.oauth2.service_account import Credentials
    import gspread

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    raw_json = config.get("GOOGLE_SHEETS_CREDENTIALS_JSON") or ""
    cred_file = config.get("GOOGLE_SHEETS_CREDENTIALS_FILE") or ""

    if raw_json.strip():
        info = json.loads(raw_json)
        creds = Credentials.from_service_account_info(info, scopes=scopes)
    elif cred_file.strip():
        creds = Credentials.from_service_account_file(cred_file, scopes=scopes)
    else:
        return None

    return gspread.authorize(creds)


def _get_worksheet(config):
    spreadsheet_id = config.get("GOOGLE_SHEETS_SPREADSHEET_ID") or ""
    if not spreadsheet_id.strip():
        return None

    client = _load_credentials(config)
    if client is None:
        return None

    spreadsheet = client.open_by_key(spreadsheet_id)
    worksheet_name = config.get("GOOGLE_SHEETS_WORKSHEET") or "reports"
    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
    except Exception:  # worksheet doesn't exist yet
        worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=100, cols=len(HEADER))

    return worksheet


def _ensure_header(worksheet):
    first_row = worksheet.row_values(1)
    if first_row != HEADER:
        worksheet.update([HEADER], "A1")


def is_configured(config):
    return bool((config.get("GOOGLE_SHEETS_SPREADSHEET_ID") or "").strip())


def sync_report(app, report):
    """Upsert one report into the configured Google Sheet. Safe to call always."""
    config = app.config
    if not is_configured(config):
        logger.info("Google Sheets sync skipped: GOOGLE_SHEETS_SPREADSHEET_ID not set")
        return False

    try:
        worksheet = _get_worksheet(config)
        if worksheet is None:
            logger.info("Google Sheets sync skipped: credentials not configured")
            return False

        _ensure_header(worksheet)
        row = report_to_row(report)

        id_column = worksheet.col_values(1)  # includes header in row 1
        target_row = None
        for idx, value in enumerate(id_column[1:], start=2):
            if value == str(report.id):
                target_row = idx
                break

        if target_row:
            worksheet.update([row], f"A{target_row}")
        else:
            worksheet.append_row(row, value_input_option="USER_ENTERED")
        return True
    except Exception as exc:  # never let a sheet problem break the save
        logger.exception("Google Sheets sync failed for report id=%s: %s", getattr(report, "id", "?"), exc)
        return False


def sync_all(app, reports):
    """Backfill: push a batch of reports (used by the CLI command)."""
    ok = 0
    for report in reports:
        if sync_report(app, report):
            ok += 1
    return ok
