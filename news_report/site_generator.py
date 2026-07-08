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


def _group_by_source(articles: list[dict]) -> list[dict]:
    """Groups a province's articles by source, domestic outlets first.

    Preserves first-seen order within each origin group (stable sort).
    """
    order: list[str] = []
    groups: dict[str, dict] = {}
    for article in articles:
        source = article["source"]
        if source not in groups:
            groups[source] = {
                "source": source,
                "origin": article.get("source_origin", "domestic"),
                "articles": [],
            }
            order.append(source)
        groups[source]["articles"].append(article)

    order.sort(key=lambda source: groups[source]["origin"] != "domestic")
    return [groups[source] for source in order]


def _build_render_report(report: dict) -> dict:
    provinces = {
        province: {"total": len(articles), "sources": _group_by_source(articles)}
        for province, articles in report["provinces"].items()
    }
    return {"date": report["date"], "provinces": provinces}


def generate_site(
    reports_dir: str | Path = DEFAULT_REPORTS_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    templates_dir: str | Path = DEFAULT_TEMPLATES_DIR,
) -> None:
    reports = _load_all_reports(reports_dir)
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html"]),
    )

    output_path = Path(output_dir)
    (output_path / "reports").mkdir(parents=True, exist_ok=True)

    daily_template = env.get_template("daily.html")
    for report in reports:
        html = daily_template.render(report=_build_render_report(report))
        (output_path / "reports" / f"{report['date']}.html").write_text(html, encoding="utf-8")

    reports_newest_first = sorted(reports, key=lambda r: r["date"], reverse=True)
    index_template = env.get_template("index.html")
    index_html = index_template.render(reports=reports_newest_first)
    (output_path / "index.html").write_text(index_html, encoding="utf-8")
