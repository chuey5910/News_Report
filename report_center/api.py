from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

from .models import NewsReport

bp = Blueprint("api", __name__, url_prefix="/api")


def _require_api_key():
    supplied = request.headers.get("X-API-Key", "")
    expected = current_app.config.get("API_KEY", "")
    return supplied and expected and supplied == expected


def _serialize(item):
    return {
        "id": item.id,
        "report_type": {
            "advance": item.is_advance_news,
            "closure": item.is_closure,
            "incident": item.is_incident_report,
            "general": item.is_general_news,
        },
        "title": item.title,
        "activity_types": item.activity_types,
        "problem_group_types": item.problem_group_types,
        "location": item.location,
        "event_datetime": item.event_datetime.isoformat() if item.event_datetime else None,
        "event_end_datetime": item.event_end_datetime.isoformat() if item.event_end_datetime else None,
        "mass_count": item.mass_count,
        "demands": item.demands,
        "leaders": [leader.full_name for leader in item.leaders],
        "vehicles": [
            {
                "vehicle_type": v.vehicle_type,
                "plate_number": v.plate_number,
                "province": v.province,
                "color": v.color,
            }
            for v in item.vehicles
        ],
        "created_at": item.created_at.isoformat(),
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

    type_column_map = {
        "advance": NewsReport.is_advance_news,
        "closure": NewsReport.is_closure,
        "incident": NewsReport.is_incident_report,
        "general": NewsReport.is_general_news,
    }
    type_param = request.args.get("type")
    if type_param and type_param not in type_column_map:
        return jsonify({"error": f"unknown type '{type_param}'"}), 400

    limit = request.args.get("limit", 50, type=int)

    query = NewsReport.query
    if since is not None:
        query = query.filter(NewsReport.created_at > since)
    if type_param:
        query = query.filter(type_column_map[type_param].is_(True))

    items = query.order_by(NewsReport.created_at.desc()).limit(limit).all()
    results = [_serialize(item) for item in items]
    return jsonify({"count": len(results), "results": results})
