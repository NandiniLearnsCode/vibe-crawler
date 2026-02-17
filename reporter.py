"""
Vibe Crawler — Report Generation
=================================
Produces terminal, JSON, and HTML reports from crawl results.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from crawler import CrawlResult, Bug


def print_report(result: CrawlResult) -> None:
    """Pretty-print findings to the terminal."""
    print("\n" + "=" * 60)
    print(f"  VIBE CRAWLER REPORT — {result.start_url}")
    print(f"  Pages visited: {result.pages_visited}")
    print(f"  Bugs found:    {len(result.bugs)}")
    print("=" * 60)

    by_severity: dict[str, list[Bug]] = {}
    for bug in result.bugs:
        by_severity.setdefault(bug.severity.value, []).append(bug)

    for sev in ["critical", "high", "medium", "low", "info"]:
        bugs = by_severity.get(sev, [])
        if not bugs:
            continue
        icon = "🔴" if sev in ("critical", "high") else "🟡" if sev == "medium" else "🔵"
        print(f"\n{icon} {sev.upper()} ({len(bugs)})")
        for bug in bugs:
            print(f"  [{bug.category}] {bug.title}")
            print(f"    URL: {bug.url}")
            print(f"    {bug.description[:120]}")

    if result.errors:
        print(f"\n⚠️  CRAWLER ERRORS ({len(result.errors)})")
        for err in result.errors:
            print(f"  {err[:120]}")

    print()


def generate_json_report(result: CrawlResult, output_path: str = "report.json") -> dict:
    """Write findings to a JSON file."""
    data = {
        "tool": "Vibe Crawler",
        "start_url": result.start_url,
        "pages_visited": result.pages_visited,
        "started_at": result.started_at,
        "finished_at": result.finished_at,
        "summary": {
            "total_bugs": len(result.bugs),
            "by_severity": {},
            "by_category": {},
        },
        "bugs": [],
        "errors": result.errors,
    }
    for bug in result.bugs:
        data["bugs"].append(asdict(bug))
        data["summary"]["by_severity"][bug.severity.value] = (
            data["summary"]["by_severity"].get(bug.severity.value, 0) + 1
        )
        data["summary"]["by_category"][bug.category] = (
            data["summary"]["by_category"].get(bug.category, 0) + 1
        )

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, default=str)

    print(f"📄 JSON report saved to {output_path}")
    return data


def generate_html_report(result: CrawlResult, output_path: str = "report.html") -> None:
    """Generate a self-contained HTML report with filtering and sorting."""

    severity_colors = {
        "critical": "#dc2626",
        "high": "#ea580c",
        "medium": "#ca8a04",
        "low": "#2563eb",
        "info": "#6b7280",
    }

    bug_rows = ""
    for bug in result.bugs:
        color = severity_colors.get(bug.severity.value, "#6b7280")
        desc = bug.description.replace("<", "&lt;").replace(">", "&gt;")
        bug_rows += f"""
        <tr data-severity="{bug.severity.value}" data-category="{bug.category}">
            <td><span class="badge" style="background:{color}">{bug.severity.value.upper()}</span></td>
            <td>{bug.category}</td>
            <td>{bug.title}</td>
            <td class="desc">{desc}</td>
            <td class="url"><a href="{bug.url}" target="_blank">{bug.url}</a></td>
        </tr>"""

    # Severity summary counts
    sev_counts = {}
    cat_counts = {}
    for bug in result.bugs:
        sev_counts[bug.severity.value] = sev_counts.get(bug.severity.value, 0) + 1
        cat_counts[bug.category] = cat_counts.get(bug.category, 0) + 1

    summary_badges = ""
    for sev in ["critical", "high", "medium", "low", "info"]:
        count = sev_counts.get(sev, 0)
        if count:
            color = severity_colors[sev]
            summary_badges += (
                f'<span class="badge" style="background:{color}">'
                f"{sev.upper()}: {count}</span> "
            )

    category_badges = ""
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        category_badges += f'<span class="badge badge-cat">{cat}: {count}</span> '

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vibe Crawler Report — {result.start_url}</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
           sans-serif; background: #0f172a; color: #e2e8f0; padding: 2rem; }}
    h1 {{ font-size: 1.8rem; margin-bottom: 0.25rem; }}
    .subtitle {{ color: #94a3b8; margin-bottom: 1.5rem; }}
    .stats {{ display: flex; gap: 2rem; margin-bottom: 1.5rem; flex-wrap: wrap; }}
    .stat {{ background: #1e293b; border-radius: 8px; padding: 1rem 1.5rem; }}
    .stat-value {{ font-size: 1.5rem; font-weight: 700; }}
    .stat-label {{ color: #94a3b8; font-size: 0.85rem; }}
    .badges {{ margin-bottom: 1rem; }}
    .badge {{ display: inline-block; padding: 0.2rem 0.6rem; border-radius: 4px;
              font-size: 0.75rem; font-weight: 600; color: white; margin: 2px; }}
    .badge-cat {{ background: #334155; color: #e2e8f0; }}
    .filters {{ margin-bottom: 1rem; display: flex; gap: 0.5rem; flex-wrap: wrap; }}
    .filters select {{ background: #1e293b; color: #e2e8f0; border: 1px solid #334155;
                       padding: 0.4rem 0.8rem; border-radius: 6px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th {{ text-align: left; padding: 0.6rem 0.8rem; background: #1e293b;
         border-bottom: 2px solid #334155; font-size: 0.8rem;
         text-transform: uppercase; color: #94a3b8; }}
    td {{ padding: 0.6rem 0.8rem; border-bottom: 1px solid #1e293b;
         font-size: 0.85rem; vertical-align: top; }}
    tr:hover {{ background: #1e293b; }}
    .desc {{ max-width: 350px; word-break: break-word; }}
    .url {{ max-width: 250px; word-break: break-all; }}
    a {{ color: #60a5fa; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
    <h1>🐛 Vibe Crawler Report</h1>
    <p class="subtitle">{result.start_url}</p>

    <div class="stats">
        <div class="stat">
            <div class="stat-value">{result.pages_visited}</div>
            <div class="stat-label">Pages Visited</div>
        </div>
        <div class="stat">
            <div class="stat-value">{len(result.bugs)}</div>
            <div class="stat-label">Bugs Found</div>
        </div>
        <div class="stat">
            <div class="stat-value">{sev_counts.get('critical', 0) + sev_counts.get('high', 0)}</div>
            <div class="stat-label">Critical + High</div>
        </div>
    </div>

    <div class="badges">{summary_badges}</div>
    <div class="badges">{category_badges}</div>

    <div class="filters">
        <select id="filterSeverity" onchange="applyFilters()">
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
            <option value="info">Info</option>
        </select>
        <select id="filterCategory" onchange="applyFilters()">
            <option value="">All Categories</option>
            {"".join(f'<option value="{cat}">{cat}</option>' for cat in sorted(cat_counts.keys()))}
        </select>
    </div>

    <table>
        <thead>
            <tr>
                <th>Severity</th>
                <th>Category</th>
                <th>Title</th>
                <th>Description</th>
                <th>URL</th>
            </tr>
        </thead>
        <tbody id="bugTable">
            {bug_rows}
        </tbody>
    </table>

    <script>
        function applyFilters() {{
            const sev = document.getElementById('filterSeverity').value;
            const cat = document.getElementById('filterCategory').value;
            document.querySelectorAll('#bugTable tr').forEach(row => {{
                const matchSev = !sev || row.dataset.severity === sev;
                const matchCat = !cat || row.dataset.category === cat;
                row.style.display = (matchSev && matchCat) ? '' : 'none';
            }});
        }}
    </script>
</body>
</html>"""

    with open(output_path, "w") as f:
        f.write(html)

    print(f"🌐 HTML report saved to {output_path}")
