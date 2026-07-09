from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

from .models import REPORT_CATEGORIES

bp = Blueprint("api", __name__, url_prefix="/api")


def _require_api_key():
    supplied = request.headers.get("X-API-Key", "")
    expected = current_app.config.get("API_KEY", "")
    return supplied and expected and supplied == expected


def _detail_text(category, item):
    if category in ("advance", "closure"):
        return item.demands
    return item.what  # situation, general (5W1H)


def _serialize(category, item):
    data = {
        "category": category,
        "category_label": REPORT_CATEGORIES[category]["label"],
        "id": item.id,
        "title": item.title,
        "detail": _detail_text(category, item),
        "created_at": item.created_at.isoformat(),
        "created_by": item.created_by.full_name if item.created_by else None,
    }
    if category in ("advance", "closure"):
        data["location"] = item.location
        data["event_datetime"] = item.event_datetime.isoformat() if item.event_datetime else None
        data["event_end_datetime"] = item.event_end_datetime.isoformat() if item.event_end_datetime else None
        data["mass_count"] = item.mass_count
        data["leaders"] = [leader.full_name for leader in item.leaders]
        data["vehicles"] = [
            {
                "vehicle_type": v.vehicle_type,
                "plate_number": v.plate_number,
                "province": v.province,
                "color": v.color,
            }
            for v in item.vehicles
        ]
        if category == "closure":
            data["related_advance_id"] = item.related_advance_id
    if category in ("situation", "general"):
        data["who"] = item.who
        data["when"] = item.when.isoformat() if item.when else None
        data["where"] = item.where
        data["why"] = item.why
        data["how"] = item.how
    return data


@bp.route("/reports/latest")
def latest_reports():
    """JSON feed for external systems (e.g. the RSS news_report pipeline) to
    pull newly-recorded reports for LINE notification purposes.

    Auth: header `X-API-Key: <REPORT_CENTER_API_KEY>`
    Query params:
      - since: ISO 8601 timestamp, only return reports created after this
      - category: one of advance|closure|situation|general (default: all)
      - limit: max items per category (default 50)
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

    category_param = request.args.get("category")
    if category_param and category_param not in REPORT_CATEGORIES:
        return jsonify({"error": f"unknown category '{category_param}'"}), 400

    limit = request.args.get("limit", 50, type=int)
    categories = [category_param] if category_param else list(REPORT_CATEGORIES.keys())

    results = []
    for category in categories:
        model = REPORT_CATEGORIES[category]["model"]
        query = model.query
        if since is not None:
            query = query.filter(model.created_at > since)
        items = query.order_by(model.created_at.desc()).limit(limit).all()
        results.extend(_serialize(category, item) for item in items)

    results.sort(key=lambda r: r["created_at"], reverse=True)
    return jsonify({"count": len(results), "results": results})
