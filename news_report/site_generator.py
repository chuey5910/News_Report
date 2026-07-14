import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

DEFAULT_TEMPLATES_DIR = "templates"
DEFAULT_REPORTS_DIR = "data/reports"
DEFAULT_OUTPUT_DIR = "docs"


def _load_all_reports(reports_dir: str | Path) -> list[dict]:
    reports = []
    for path in sorted(Path(reports_dir).glob("*.json")):
        with open(path, encoding="utf-8") as f:
            reports.append(json.load(f))
    return reports


def generate_site(
    reports_dir: str | Path = DEFAULT_REPORTS_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    templates_dir: str | Path = DEFAULT_TEMPLATES_DIR,
) -> None:
    """Publishes report JSON under docs/data/ and the single-page app shell at docs/index.html.

    The app (templates/index.html) fetches docs/data/index.json for the list of
    available dates, then docs/data/<date>.json for that day's articles, and does
    all filtering/grouping/search client-side — no server-side per-date pages.
    """
    reports = _load_all_reports(reports_dir)

    output_path = Path(output_dir)
    data_dir = output_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    dates_newest_first = sorted((r["date"] for r in reports), reverse=True)
    for report in reports:
        with open(data_dir / f"{report['date']}.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False)
    with open(data_dir / "index.json", "w", encoding="utf-8") as f:
        json.dump(dates_newest_first, f)

    # Reports purged from data/reports/ (older than the 7-day retention window)
    # must disappear from the site too, or the date dropdown would 404.
    current_dates = set(dates_newest_first)
    for stale in data_dir.glob("*.json"):
        if stale.name != "index.json" and stale.stem not in current_dates:
            stale.unlink()

    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html"]),
    )
    index_html = env.get_template("index.html").render()
    (output_path / "index.html").write_text(index_html, encoding="utf-8")
