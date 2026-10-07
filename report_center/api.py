from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

from . import permissions
from .models import REPORT_TYPE_LABELS, NewsReport

bp = Blueprint("api", __name__, url_prefix="/api")


def _require_api_key():
    supplied = request.headers.get("X-API-Key", "")
    expected = current_app.config.get("API_KEY", "")
    return supplied and expected and supplied == expected


def _serialize(item):
    return {
        "id": item.id,
        "ref_number": item.ref_number,
        "report_type": item.report_type,
        "report_type_label": REPORT_TYPE_LABELS.get(item.report_type, item.report_type),
        "special_branch_province": item.special_branch_province,
        "title": item.title,
        "activity_types": item.activity_types,
        "problem_group_types": item.problem_group_types,
        "location": item.location,
        "latitude": item.latitude,
        "longitude": item.longitude,
        "situation_level": item.situation_level,
        "event_datetime": item.event_datetime.isoformat() if item.event_datetime else None,
        "event_end_datetime": item.event_end_datetime.isoformat() if item.event_end_datetime else None,
        "mass_count": item.mass_count,
        "mass_members": item.mass_members,
        "mass_media": item.mass_media,
        "mass_others": item.mass_others,
        "demands": item.demands,
        "activity_detail": item.activity_detail,
        "activity_format": item.activity_format,
        "supporters": item.supporters,
        "affiliations": item.affiliations,
        "permit_status": item.permit_status,
        "permit_location": item.permit_location,
        "permit_duration_days": item.permit_duration_days,
        "overnight_equipment_status": item.overnight_equipment_status,
        "overnight_equipment_detail": item.overnight_equipment_detail,
        "vehicle_status": item.vehicle_status,
        "other_info": item.other_info,
        "trend_assessment": item.trend_assessment,
        "considerations": item.considerations,
        "reporter_name": item.reporter_name,
        "reporter_phone": item.reporter_phone,
        "leaders": [
            {"full_name": leader.full_name, "position": leader.position, "role": leader.role}
            for leader in item.leaders
        ],
        "vehicles": [
            {
                "vehicle_type": v.vehicle_type,
                "plate_number": v.plate_number,
                "province": v.province,
                "color": v.color,
                "owner": v.owner,
                "usage": v.usage,
            }
            for v in item.vehicles
        ],
        "people": [
            {
                "kind": p.kind,
                "category": p.category,
                "full_name": p.full_name,
                "group_name": p.group_name,
                "role": p.role,
            }
            for p in item.people
        ],
        "media_posts": [
            {"page_name": m.page_name, "likes": m.likes, "shares": m.shares}
            for m in item.media_posts
        ],
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        "verified_at": item.verified_at.isoformat() if item.verified_at else None,
        "created_by": item.created_by.full_name if item.created_by else None,
    }


@bp.route("/reports/latest")
def latest_reports():
    """JSON feed for external systems (e.g. the RSS news_report pipeline) to
    pull newly-recorded reports for LINE notification purposes.

    Auth: header `X-API-Key: <REPORT_CENTER_API_KEY>`
    Query params:
      - since: ISO 8601 timestamp, only return reports created after this
      - type: one of advance|closure|incident|general — filter by ประเภทรายงาน
      - limit: max items (default 50)
      - by: "updated" → ใช้กับ since เทียบ "เวลาแก้ไขล่าสุด" แทนเวลาสร้าง และเรียงจากเก่าไปใหม่
            (ให้เว็บข้อมูลบุคคลดึงรายงานที่ยืนยันทีหลัง/แก้ไขทีหลังได้ครบ ทีละชุดจนหมด)
    """
    if not _require_api_key():
        return jsonify({"error": "unauthorized"}), 401

    since_param = request.args.get("since")
    since = None
    if since_param:
        try:
            since = datetime.fromisoformat(since_param)
        except ValueError:
            return jsonify({"error": "invalid 'since' timestamp, expected ISO 8601"}), 400

    type_param = request.args.get("type")
    if type_param and type_param not in REPORT_TYPE_LABELS:
        return jsonify({"error": f"unknown type '{type_param}'"}), 400

    limit = request.args.get("limit", 50, type=int)

    by_updated = request.args.get("by") == "updated"
    query = permissions.verified_only(NewsReport.query)   # รายงานที่ยังไม่ยืนยันไม่ออกทาง API
    if since is not None:
        query = query.filter((NewsReport.updated_at if by_updated else NewsReport.created_at) > since)
    if type_param:
        query = query.filter(NewsReport.report_type == type_param)

    if by_updated:
        items = query.order_by(NewsReport.updated_at.asc(), NewsReport.id.asc()).limit(limit).all()
    else:
        items = query.order_by(NewsReport.created_at.desc()).limit(limit).all()
    results = [_serialize(item) for item in items]
    return jsonify({"count": len(results), "results": results})
