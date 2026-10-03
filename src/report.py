"""
report.py
---------
Builds a self-contained HTML analysis report that can be downloaded,
opened in any browser and printed to PDF (Ctrl + P -> Save as PDF).
"""

from datetime import datetime
from html import escape

from src.analysis import format_kpi

CSS = """
body{font-family:Segoe UI,Arial,sans-serif;color:#1d2733;max-width:960px;margin:40px auto;padding:0 24px;line-height:1.55}
h1{color:#1F4E79;margin-bottom:4px} h2{color:#1F4E79;border-bottom:2px solid #dbe4ee;padding-bottom:6px;margin-top:40px}
.muted{color:#5b6b7c} .kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.kpi{border:1px solid #dbe4ee;border-radius:8px;padding:14px} .kpi b{display:block;font-size:22px;color:#1F4E79}
table{border-collapse:collapse;width:100%;font-size:14px} th,td{border-bottom:1px solid #e5ebf1;padding:8px;text-align:left;vertical-align:top}
th{background:#f3f6f9} .warn{color:#b45309;font-weight:600} .ok{color:#15803d;font-weight:600}
.insight{border-left:4px solid #1F4E79;padding:8px 14px;margin:14px 0;background:#f8fafc}
@media print{.chart{page-break-inside:avoid}}
"""


def build_html_report(name, profile, kpis, quality, insights, figures, cleaning_log, ai_summary=None) -> str:
    parts = [f"<!doctype html><html><head><meta charset='utf-8'><title>Analysis report – {escape(name)}</title>"
             f"<style>{CSS}</style></head><body>",
             f"<h1>Data Analysis Report</h1><p class='muted'>Dataset: <b>{escape(name)}</b> · "
             f"Generated {datetime.now():%d %B %Y, %H:%M} with AI Data Analyst</p>"]

    # 1. Overview
    parts.append("<h2>1. Dataset overview</h2><table>")
    for label, value in [("Rows", f"{profile['rows']:,}"), ("Columns", profile["columns"]),
                         ("Missing values", f"{profile['missing_values']:,}"),
                         ("Duplicate rows", f"{profile['duplicate_rows']:,}"),
                         ("Date columns", ", ".join(profile["date"]) or "None"),
                         ("Numerical columns", ", ".join(profile["numerical"]) or "None"),
                         ("Categorical columns", ", ".join(profile["categorical"]) or "None")]:
        parts.append(f"<tr><th>{label}</th><td>{escape(str(value))}</td></tr>")
    parts.append("</table>")

    # 2. KPIs
    if kpis:
        parts.append("<h2>2. Key performance indicators</h2><div class='kpis'>")
        parts += [f"<div class='kpi'>{escape(k)}<b>{format_kpi(k, v)}</b></div>" for k, v in kpis.items()]
        parts.append("</div><p class='muted'>Calculated on the cleaned data (see section 3).</p>")

    # 3. Data quality
    parts.append("<h2>3. Data quality</h2><table><tr><th>Check</th><th>Count</th><th>Status</th><th>What it means</th></tr>")
    for item in quality:
        cls = "warn" if item["status"] == "warning" else "ok"
        label = "Review" if item["status"] == "warning" else "OK"
        parts.append(f"<tr><td>{escape(item['check'])}</td><td>{item['count']:,}</td>"
                     f"<td class='{cls}'>{label}</td><td>{escape(item['consequence'])}</td></tr>")
    parts.append("</table><p><b>Cleaning steps applied:</b></p><ul>")
    parts += [f"<li>{escape(step)}</li>" for step in cleaning_log]
    parts.append("</ul>")

    # 4. Charts
    if figures:
        parts.append("<h2>4. Charts</h2>")
        for i, fig in enumerate(figures):
            html = fig.to_html(full_html=False, include_plotlyjs="cdn" if i == 0 else False)
            parts.append(f"<div class='chart'>{html}</div>")

    # 5. Findings
    parts.append("<h2>5. Key findings</h2><p class='muted'>Calculated facts from the data, with why each one matters.</p>")
    for ins in insights:
        parts.append(f"<div class='insight'><b>{escape(ins['title'])}</b><br>{escape(ins['fact'])}"
                     f"<br><span class='muted'>Why it matters: {escape(ins['why'])}</span></div>")

    # 6. Recommendations
    parts.append("<h2>6. Business recommendations</h2>")
    if ai_summary:
        parts.append(f"<p>{escape(ai_summary.get('summary', ''))}</p><ol>")
        for rec in ai_summary.get("recommendations", []):
            parts.append(f"<li><b>{escape(rec.get('title', ''))}</b>: {escape(rec.get('action', ''))} "
                         f"<span class='muted'>(based on: {escape(rec.get('based_on', ''))})</span></li>")
        parts.append("</ol><p class='muted'>Recommendations drafted by AI from the calculated findings above "
                     "and reviewed against them. Interpretations, not facts.</p>")
    else:
        parts.append("<p class='muted'>Generate AI recommendations on the Business Insights page to include "
                     "them here. Each finding above already explains why it matters.</p>")
    parts.append("</body></html>")
    return "\n".join(parts)
