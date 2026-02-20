#!/usr/bin/env python3
"""
Generator script: Parse markdown export -> self-contained HTML report.
Deliberate shortcut: data hardcoded via parsing at generation time.
Run once, produces SPIKE-attachment-format-evaluation.html.
"""
import json
import re
import sys
from pathlib import Path

MD_FILE = Path("/Users/tomtenuta/Downloads/insights_export_Natural_Medicine_and_Chiropractic_Specialties_20260219.md")
OUT_FILE = Path("/Users/tomtenuta/Code/autom8y-asana/docs/spikes/SPIKE-attachment-format-evaluation.html")

STRIP_COLS = {"Office Phone", "Vertical", "Office"}


def parse_md_tables(text: str) -> dict:
    """Parse all ## sections with pipe tables. Returns {section_name: {headers, rows}}."""
    sections = {}
    # Split on ## headers
    parts = re.split(r'^## (.+)$', text, flags=re.MULTILINE)
    # parts[0] = preamble, then pairs of (name, content)
    i = 1
    while i < len(parts) - 1:
        name = parts[i].strip()
        content = parts[i + 1]
        i += 2
        lines = content.strip().split('\n')
        table_lines = [l for l in lines if l.startswith('|')]
        if len(table_lines) < 3:
            sections[name] = {"headers": [], "rows": []}
            continue
        header_line = table_lines[0]
        # skip separator line (table_lines[1])
        data_lines = table_lines[2:]
        raw_headers = [h.strip() for h in header_line.strip('|').split('|')]
        # Build column indices to keep (strip redundant cols)
        keep_idx = [i2 for i2, h in enumerate(raw_headers) if h not in STRIP_COLS]
        headers = [raw_headers[i2] for i2 in keep_idx]
        rows = []
        for line in data_lines:
            if not line.strip() or line.strip() == '|':
                continue
            # Handle multi-line rows: join continuation lines
            cells_raw = line.strip('|').split('|')
            # Pad if needed
            while len(cells_raw) < len(raw_headers):
                cells_raw.append('')
            cells = [cells_raw[i2].strip() if i2 < len(cells_raw) else '' for i2 in keep_idx]
            rows.append(cells)
        sections[name] = {"headers": headers, "rows": rows}
    return sections


def compute_kpis(summary_rows, summary_headers):
    """Compute KPI values from SUMMARY table rows."""
    try:
        idx = {h: i for i, h in enumerate(summary_headers)}
        spend_i = idx.get('Spend')
        leads_i = idx.get('Leads')
        scheds_i = idx.get('Scheds')
        br_i = idx.get('Booking Rate')
        start_i = idx.get('Period Start')

        total_spend = 0.0
        total_leads = 0
        total_scheds = 0
        booking_rates = []
        spend_series = []
        br_series = []
        dates = []

        for row in summary_rows:
            try:
                sp = float(row[spend_i]) if row[spend_i] not in ('---', '', None) else 0
                total_spend += sp
                spend_series.append(sp)
            except (ValueError, TypeError, IndexError):
                spend_series.append(0)

            try:
                total_leads += int(row[leads_i]) if row[leads_i] not in ('---', '', None) else 0
            except (ValueError, TypeError, IndexError):
                pass

            try:
                total_scheds += int(row[scheds_i]) if row[scheds_i] not in ('---', '', None) else 0
            except (ValueError, TypeError, IndexError):
                pass

            try:
                br_val = row[br_i] if br_i is not None else '---'
                if br_val not in ('---', '', None):
                    br = float(br_val)
                    booking_rates.append(br)
                    br_series.append(br)
                else:
                    br_series.append(None)
            except (ValueError, TypeError, IndexError):
                br_series.append(None)

            try:
                dates.append(row[start_i] if start_i is not None else '')
            except IndexError:
                dates.append('')

        avg_br = sum(booking_rates) / len(booking_rates) if booking_rates else 0
        best_br = max(booking_rates) if booking_rates else 0
        worst_br = min(booking_rates) if booking_rates else 0

        # Find best/worst week dates
        best_week = worst_week = ''
        if br_i is not None and start_i is not None:
            for row in summary_rows:
                try:
                    br_val = row[br_i]
                    if br_val not in ('---', '', None):
                        br = float(br_val)
                        if abs(br - best_br) < 0.01:
                            best_week = row[start_i]
                        if abs(br - worst_br) < 0.01 and worst_week == '':
                            worst_week = row[start_i]
                except (ValueError, TypeError, IndexError):
                    pass

        # Spend trend: last 12 weeks vs prior 12
        recent = spend_series[:12]
        prior = spend_series[12:24]
        trend = 'up' if sum(recent) >= sum(prior) else 'down'

        return {
            'total_spend': total_spend,
            'total_leads': total_leads,
            'total_scheds': total_scheds,
            'avg_br': avg_br,
            'best_br': best_br,
            'worst_br': worst_br,
            'best_week': best_week,
            'worst_week': worst_week,
            'trend': trend,
            'spend_series': spend_series[:52],   # last ~year
            'br_series': br_series[:52],
        }
    except Exception as e:
        return {
            'total_spend': 0, 'total_leads': 0, 'total_scheds': 0,
            'avg_br': 0, 'best_br': 0, 'worst_br': 0,
            'best_week': '', 'worst_week': '',
            'trend': 'flat', 'spend_series': [], 'br_series': [],
        }


def make_sparkline(values, width=120, height=30, color='#4a7bb5'):
    """Generate an inline SVG sparkline for a list of numeric values (None=skip)."""
    nums = [v for v in values if v is not None]
    if len(nums) < 2:
        return f'<svg width="{width}" height="{height}"></svg>'
    mn = min(nums)
    mx = max(nums)
    rng = mx - mn if mx != mn else 1
    pts = []
    n = len(values)
    for i, v in enumerate(values):
        if v is None:
            continue
        x = int(i / (n - 1) * (width - 4)) + 2
        y = int((1 - (v - mn) / rng) * (height - 4)) + 2
        pts.append(f"{x},{y}")
    polyline = ' '.join(pts)
    return (f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'xmlns="http://www.w3.org/2000/svg">'
            f'<polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="1.5" '
            f'stroke-linejoin="round" stroke-linecap="round"/>'
            f'</svg>')


def escape_html(s: str) -> str:
    return (s.replace('&', '&amp;')
             .replace('<', '&lt;')
             .replace('>', '&gt;')
             .replace('"', '&quot;'))


def cell_class(header: str, value: str) -> str:
    """Return CSS class for conditional formatting."""
    classes = []
    h_lower = header.lower()
    if value == '---' or value == '':
        classes.append('muted')
        return ' '.join(classes)
    # Numeric alignment
    try:
        float(value)
        if 'spend' in h_lower or 'cpl' in h_lower or 'cps' in h_lower or 'ecps' in h_lower or 'ltv' in h_lower or 'budget' in h_lower or 'cost' in h_lower or 'roas' in h_lower:
            classes.append('num')
            # Heat for spend
            if 'spend' in h_lower:
                classes.append('spend-cell')
        elif 'booking rate' in h_lower or 'conversion rate' in h_lower or 'sched rate' in h_lower or 'conv rate' in h_lower:
            classes.append('num')
            try:
                v = float(value)
                # May be 0-100 or 0-1
                if v > 1:
                    # percentage form
                    if v >= 40:
                        classes.append('br-green')
                    elif v >= 20:
                        classes.append('br-yellow')
                    else:
                        classes.append('br-red')
                else:
                    # decimal form
                    if v >= 0.4:
                        classes.append('br-green')
                    elif v >= 0.2:
                        classes.append('br-yellow')
                    else:
                        classes.append('br-red')
            except ValueError:
                pass
        elif any(x in h_lower for x in ['leads', 'scheds', 'convs', 'pen', 'imp', 'lclicks', 'contacts', 'ns ']):
            classes.append('num')
        else:
            classes.append('num')
    except ValueError:
        # Date
        if re.match(r'\d{4}-\d{2}-\d{2}', value):
            classes.append('date-cell')
    return ' '.join(classes)


def render_table(section_id: str, headers: list, rows: list, max_col_width: int = 300) -> str:
    """Render an HTML table for a section."""
    if not headers:
        return '<p class="empty">No data.</p>'

    thead_cells = ''.join(
        f'<th onclick="sortTable(\'{section_id}\',{i})" '
        f'title="Click to sort">{escape_html(h)}<span class="sort-icon"></span></th>'
        for i, h in enumerate(headers)
    )
    tbody_rows = []
    for row in rows:
        cells = []
        for i, h in enumerate(headers):
            val = row[i] if i < len(row) else ''
            cls = cell_class(h, val)
            display = escape_html(val) if val != '---' else '<span class="dash">—</span>'
            # Truncate very long cells (transcripts)
            if len(val) > 200 and 'transcript' in h.lower():
                display = f'<span title="{escape_html(val[:500])}">{escape_html(val[:197])}...</span>'
            cells.append(f'<td class="{cls}">{display}</td>')
        tbody_rows.append('<tr>' + ''.join(cells) + '</tr>')

    tbody = '\n'.join(tbody_rows)
    return f'''<table id="tbl-{section_id}" class="data-table">
  <thead><tr>{thead_cells}</tr></thead>
  <tbody>{tbody}</tbody>
</table>'''


def generate_html(sections: dict, kpis: dict) -> str:
    office = "Natural Medicine and Chiropractic Specialties"
    phone = "+1 678-513-0095"
    generated = "2026-02-19"

    # Section order and display names
    section_order = [
        ("SUMMARY", "Summary"),
        ("BY QUARTER", "By Quarter"),
        ("BY MONTH", "By Month"),
        ("BY WEEK", "By Week"),
        ("AD QUESTIONS", "Ad Questions"),
        ("OFFER TABLE", "Offer Table"),
        ("ASSET TABLE", "Asset Table"),
        ("APPOINTMENTS", "Appointments"),
        ("LEADS", "Leads"),
        ("UNUSED ASSETS", "Unused Assets"),
    ]

    # Build section nav items
    nav_items = []
    for key, display in section_order:
        sec = sections.get(key, {})
        row_count = len(sec.get('rows', []))
        sid = key.lower().replace(' ', '-')
        nav_items.append(
            f'<a href="#sec-{sid}" class="nav-link">'
            f'{escape_html(display)}'
            f'<span class="badge">{row_count}</span>'
            f'</a>'
        )

    # Build section content
    sections_html = []
    for key, display in section_order:
        sec = sections.get(key, {})
        headers = sec.get('headers', [])
        rows = sec.get('rows', [])
        row_count = len(rows)
        sid = key.lower().replace(' ', '-')
        table_html = render_table(sid, headers, rows)
        copy_btn = f'<button class="copy-btn" onclick="copyTable(\'{sid}\')">Copy TSV</button>'
        sections_html.append(f'''
<section id="sec-{sid}" class="table-section">
  <div class="section-header" onclick="toggleSection('{sid}')">
    <h2>{escape_html(display)} <span class="badge">{row_count} rows</span></h2>
    <div class="section-controls">
      {copy_btn}
      <span class="toggle-icon" id="toggle-{sid}">&#9660;</span>
    </div>
  </div>
  <div class="section-body" id="body-{sid}">
    <div class="table-scroll">{table_html}</div>
  </div>
</section>''')

    sections_html_str = '\n'.join(sections_html)
    nav_html = '\n'.join(nav_items)

    # KPI sparklines
    spend_sparkline = make_sparkline(kpis['spend_series'], width=140, height=36, color='#4a7bb5')
    br_vals = [v for v in kpis['br_series'] if v is not None]
    br_sparkline = make_sparkline(kpis['br_series'], width=140, height=36, color='#2a9a5c')
    trend_arrow = '&#8599;' if kpis['trend'] == 'up' else '&#8600;'
    trend_cls = 'trend-up' if kpis['trend'] == 'up' else 'trend-down'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Insights Report: {escape_html(office)}</title>
<style>
/* ===== CSS Custom Properties (Theme) ===== */
:root {{
  --bg: #fafafa;
  --surface: #ffffff;
  --border: #e0e0e0;
  --border-light: #f0f0f0;
  --text: #1a1a1a;
  --text-muted: #888;
  --text-dim: #bbb;
  --accent: #4a7bb5;
  --accent-hover: #3568a0;
  --header-bg: #f4f4f4;
  --zebra: #f9f9f9;
  --green: #1e7a44;
  --green-bg: #e6f4ed;
  --yellow: #7a5c00;
  --yellow-bg: #fff8e0;
  --red: #9a1f1f;
  --red-bg: #fdeaea;
  --nav-bg: #ffffff;
  --nav-border: #e8e8e8;
  --shadow: 0 1px 2px rgba(0,0,0,0.08);
  --kpi-border: #e0e0e0;
  --font: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  --mono: 'SF Mono', 'Consolas', 'Menlo', monospace;
}}
[data-theme="dark"] {{
  --bg: #1a1a1a;
  --surface: #242424;
  --border: #383838;
  --border-light: #2e2e2e;
  --text: #e8e8e8;
  --text-muted: #888;
  --text-dim: #555;
  --accent: #6fa0d4;
  --accent-hover: #85b3e0;
  --header-bg: #2a2a2a;
  --zebra: #212121;
  --green: #4ade80;
  --green-bg: #0f2e1a;
  --yellow: #fbbf24;
  --yellow-bg: #2a2000;
  --red: #f87171;
  --red-bg: #2e0f0f;
  --nav-bg: #1e1e1e;
  --nav-border: #333;
  --shadow: 0 1px 3px rgba(0,0,0,0.4);
  --kpi-border: #383838;
}}

/* ===== Reset & Base ===== */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ font-size: 13px; scroll-behavior: smooth; }}
body {{
  font-family: var(--font);
  background: var(--bg);
  color: var(--text);
  line-height: 1.4;
}}

/* ===== Layout ===== */
.layout {{
  display: flex;
  min-height: 100vh;
}}
.sidebar {{
  width: 200px;
  min-width: 200px;
  background: var(--nav-bg);
  border-right: 1px solid var(--nav-border);
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
  padding: 12px 0;
  flex-shrink: 0;
}}
.main-content {{
  flex: 1;
  min-width: 0;
  padding: 16px 20px;
  max-width: 100%;
}}
@media (max-width: 768px) {{
  .layout {{ flex-direction: column; }}
  .sidebar {{ width: 100%; height: auto; position: static; overflow-x: auto; display: flex; flex-wrap: wrap; padding: 8px; border-right: none; border-bottom: 1px solid var(--nav-border); }}
  .sidebar .nav-section-label {{ display: none; }}
  .nav-link {{ white-space: nowrap; }}
}}

/* ===== Sidebar Navigation ===== */
.nav-section-label {{
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  padding: 6px 14px 4px;
  margin-top: 4px;
}}
.nav-link {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px 14px;
  color: var(--text);
  text-decoration: none;
  font-size: 12px;
  border-left: 3px solid transparent;
  transition: background 0.1s, border-color 0.1s;
}}
.nav-link:hover {{
  background: var(--border-light);
  border-left-color: var(--accent);
  color: var(--accent);
}}
.nav-link.active {{
  border-left-color: var(--accent);
  color: var(--accent);
  background: var(--border-light);
}}
.badge {{
  font-size: 10px;
  background: var(--border);
  color: var(--text-muted);
  border-radius: 3px;
  padding: 1px 5px;
  font-weight: 500;
  flex-shrink: 0;
}}

/* ===== Header ===== */
.report-header {{
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}}
.report-title {{ font-size: 18px; font-weight: 700; margin-bottom: 4px; }}
.report-meta {{ font-size: 11px; color: var(--text-muted); }}
.header-actions {{
  display: flex;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
  align-items: center;
}}
.btn {{
  padding: 5px 12px;
  font-size: 12px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  cursor: pointer;
  border-radius: 3px;
  font-family: var(--font);
  transition: background 0.1s;
}}
.btn:hover {{ background: var(--header-bg); border-color: var(--accent); color: var(--accent); }}
.search-wrap {{ flex: 1; max-width: 300px; position: relative; }}
.search-wrap input {{
  width: 100%;
  padding: 5px 10px;
  font-size: 12px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  border-radius: 3px;
  font-family: var(--font);
  outline: none;
}}
.search-wrap input:focus {{ border-color: var(--accent); }}
.search-clear {{
  position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
  cursor: pointer; color: var(--text-muted); font-size: 14px; line-height: 1;
  display: none;
}}
.search-count {{
  font-size: 11px; color: var(--text-muted); margin-left: 8px; white-space: nowrap;
}}

/* ===== KPI Cards ===== */
.kpi-grid {{
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 20px;
}}
.kpi-card {{
  flex: 1;
  min-width: 140px;
  max-width: 240px;
  border: 1px solid var(--kpi-border);
  background: var(--surface);
  border-radius: 4px;
  padding: 10px 14px;
  box-shadow: var(--shadow);
}}
.kpi-label {{ font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); margin-bottom: 4px; }}
.kpi-value {{ font-size: 20px; font-weight: 700; color: var(--text); line-height: 1.2; }}
.kpi-sub {{ font-size: 10px; color: var(--text-muted); margin-top: 2px; }}
.kpi-sparkline {{ margin-top: 6px; }}
.trend-up {{ color: var(--green); }}
.trend-down {{ color: var(--red); }}

/* ===== Table Sections ===== */
.table-section {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 4px;
  margin-bottom: 12px;
  box-shadow: var(--shadow);
  overflow: hidden;
}}
.section-header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 14px;
  background: var(--header-bg);
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  user-select: none;
}}
.section-header h2 {{
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  display: flex;
  align-items: center;
  gap: 8px;
}}
.section-header h2 .badge {{ font-size: 10px; }}
.section-controls {{
  display: flex;
  gap: 6px;
  align-items: center;
}}
.toggle-icon {{ font-size: 10px; color: var(--text-muted); transition: transform 0.15s; }}
.toggle-icon.collapsed {{ transform: rotate(-90deg); }}
.section-body {{ overflow: hidden; }}
.section-body.collapsed {{ display: none; }}
.table-scroll {{ overflow-x: auto; }}

/* ===== Data Table ===== */
.data-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 11.5px;
  white-space: nowrap;
}}
.data-table thead th {{
  background: var(--header-bg);
  border-bottom: 1px solid var(--border);
  padding: 5px 10px;
  text-align: left;
  font-weight: 600;
  font-size: 11px;
  color: var(--text);
  cursor: pointer;
  position: sticky;
  top: 0;
  user-select: none;
}}
.data-table thead th:hover {{ color: var(--accent); }}
.sort-icon::after {{ content: ''; margin-left: 4px; }}
th.sort-asc .sort-icon::after {{ content: '▲'; }}
th.sort-desc .sort-icon::after {{ content: '▼'; }}
.data-table tbody tr {{ border-bottom: 1px solid var(--border-light); }}
.data-table tbody tr:nth-child(even) {{ background: var(--zebra); }}
.data-table tbody tr:hover {{ background: color-mix(in srgb, var(--accent) 8%, transparent); }}
.data-table td {{
  padding: 3px 10px;
  vertical-align: middle;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
}}
/* Conditional formatting */
.br-green {{ background: var(--green-bg) !important; color: var(--green); font-weight: 600; }}
.br-yellow {{ background: var(--yellow-bg) !important; color: var(--yellow); font-weight: 600; }}
.br-red {{ background: var(--red-bg) !important; color: var(--red); font-weight: 600; }}
.muted {{ color: var(--text-dim); }}
.dash {{ color: var(--text-dim); }}
.num {{ text-align: right; font-variant-numeric: tabular-nums; font-family: var(--mono); font-size: 11px; }}
.date-cell {{ text-align: center; font-family: var(--mono); font-size: 11px; color: var(--text-muted); }}
.spend-cell {{ font-variant-numeric: tabular-nums; }}

/* Search highlight */
mark.search-hl {{
  background: #ffe066;
  color: #1a1a1a;
  border-radius: 2px;
  padding: 0 1px;
}}
[data-theme="dark"] mark.search-hl {{
  background: #7a6000;
  color: #ffe066;
}}
tr.search-hidden {{ display: none; }}

/* Copy button */
.copy-btn {{
  font-size: 10px;
  padding: 3px 8px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-muted);
  cursor: pointer;
  border-radius: 3px;
  font-family: var(--font);
  transition: background 0.1s;
}}
.copy-btn:hover {{ border-color: var(--accent); color: var(--accent); }}
.copy-btn.copied {{ color: var(--green); border-color: var(--green); }}

/* Toast */
.toast {{
  position: fixed;
  bottom: 20px;
  right: 20px;
  background: #333;
  color: #fff;
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 12px;
  opacity: 0;
  transition: opacity 0.2s;
  pointer-events: none;
  z-index: 1000;
}}
.toast.show {{ opacity: 1; }}

/* ===== Print Styles ===== */
@media print {{
  .sidebar, .header-actions, .section-controls, .copy-btn {{ display: none !important; }}
  .layout {{ display: block; }}
  .main-content {{ padding: 0; }}
  .section-body.collapsed {{ display: block !important; }}
  .table-section {{ box-shadow: none; border: 1px solid #ccc; page-break-inside: avoid; margin-bottom: 20px; }}
  .data-table {{ font-size: 9px; }}
  .kpi-sparkline {{ display: none; }}
  body {{ color: #000; background: #fff; }}
  .data-table tbody tr:nth-child(even) {{ background: #f5f5f5; }}
}}

/* Empty state */
.empty {{ padding: 20px; color: var(--text-muted); font-size: 12px; text-align: center; }}
</style>
</head>
<body>
<div class="toast" id="toast"></div>
<div class="layout">

<!-- Sidebar -->
<nav class="sidebar" aria-label="Sections">
  <div class="nav-section-label">Sections</div>
  {nav_html}
</nav>

<!-- Main -->
<main class="main-content">

  <!-- Report Header -->
  <div class="report-header">
    <div class="report-title">{escape_html(office)}</div>
    <div class="report-meta">
      Phone: {escape_html(phone)} &nbsp;&bull;&nbsp;
      Vertical: chiropractic &nbsp;&bull;&nbsp;
      Generated: {escape_html(generated)}
    </div>
    <div class="header-actions">
      <div class="search-wrap">
        <input type="text" id="global-search" placeholder="Search all tables..." oninput="onSearch(this.value)" autocomplete="off">
        <span class="search-clear" id="search-clear" onclick="clearSearch()">&#x2715;</span>
      </div>
      <span class="search-count" id="search-count"></span>
      <button class="btn" onclick="window.print()">Print Report</button>
      <button class="btn" id="theme-btn" onclick="toggleTheme()">Dark Mode</button>
      <button class="btn" onclick="expandAll()">Expand All</button>
      <button class="btn" onclick="collapseAll()">Collapse All</button>
    </div>
  </div>

  <!-- KPI Cards -->
  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">Total Spend</div>
      <div class="kpi-value">${kpis['total_spend']:,.0f}</div>
      <div class="kpi-sub">All weeks on record</div>
      <div class="kpi-sparkline">{spend_sparkline}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Total Leads</div>
      <div class="kpi-value">{kpis['total_leads']:,}</div>
      <div class="kpi-sub">Across all weeks</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Total Scheduled</div>
      <div class="kpi-value">{kpis['total_scheds']:,}</div>
      <div class="kpi-sub">Appointments scheduled</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Avg Booking Rate</div>
      <div class="kpi-value">{kpis['avg_br']:.1f}%</div>
      <div class="kpi-sub">Weeks with leads</div>
      <div class="kpi-sparkline">{br_sparkline}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Best Week</div>
      <div class="kpi-value br-green">{kpis['best_br']:.1f}%</div>
      <div class="kpi-sub">{escape_html(kpis['best_week'])}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Spend Trend</div>
      <div class="kpi-value {trend_cls}">{trend_arrow}</div>
      <div class="kpi-sub">Recent vs prior 12 wks</div>
    </div>
  </div>

  <!-- Table Sections -->
  {sections_html_str}

</main>
</div>

<script>
// ===== Sort =====
const sortState = {{}};

function sortTable(sid, colIdx) {{
  const tbl = document.getElementById('tbl-' + sid);
  if (!tbl) return;
  const th = tbl.querySelectorAll('thead th');
  const key = sid + '-' + colIdx;
  const asc = sortState[key] !== 'asc';
  sortState[key] = asc ? 'asc' : 'desc';

  // Update headers
  th.forEach((h, i) => {{
    h.classList.remove('sort-asc', 'sort-desc');
    if (i === colIdx) h.classList.add(asc ? 'sort-asc' : 'sort-desc');
  }});

  const tbody = tbl.querySelector('tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  rows.sort((a, b) => {{
    const aCell = a.cells[colIdx]?.textContent?.trim() ?? '';
    const bCell = b.cells[colIdx]?.textContent?.trim() ?? '';
    // Numeric compare
    const aNum = parseFloat(aCell.replace(/[^0-9.\-]/g, ''));
    const bNum = parseFloat(bCell.replace(/[^0-9.\-]/g, ''));
    let cmp = 0;
    if (!isNaN(aNum) && !isNaN(bNum)) {{
      cmp = aNum - bNum;
    }} else {{
      // Date or string
      cmp = aCell.localeCompare(bCell, undefined, {{numeric: true}});
    }}
    return asc ? cmp : -cmp;
  }});
  rows.forEach(r => tbody.appendChild(r));
}}

// ===== Search =====
let searchTimeout = null;

function onSearch(val) {{
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => doSearch(val), 80);
  const clear = document.getElementById('search-clear');
  if (clear) clear.style.display = val ? 'block' : 'none';
}}

function clearSearch() {{
  const inp = document.getElementById('global-search');
  if (inp) {{ inp.value = ''; doSearch(''); }}
  const clear = document.getElementById('search-clear');
  if (clear) clear.style.display = 'none';
}}

function doSearch(query) {{
  const q = query.trim().toLowerCase();
  const countEl = document.getElementById('search-count');
  if (!q) {{
    // Remove all highlights
    document.querySelectorAll('mark.search-hl').forEach(m => {{
      m.outerHTML = m.innerHTML;
    }});
    document.querySelectorAll('tr.search-hidden').forEach(r => r.classList.remove('search-hidden'));
    if (countEl) countEl.textContent = '';
    return;
  }}

  let totalMatch = 0;
  document.querySelectorAll('.data-table tbody tr').forEach(row => {{
    const text = row.textContent.toLowerCase();
    if (text.includes(q)) {{
      row.classList.remove('search-hidden');
      totalMatch++;
    }} else {{
      row.classList.add('search-hidden');
    }}
  }});

  // Highlight visible cells
  document.querySelectorAll('mark.search-hl').forEach(m => {{
    m.outerHTML = m.innerHTML;
  }});
  const re = new RegExp('(' + q.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&') + ')', 'gi');
  document.querySelectorAll('.data-table tbody tr:not(.search-hidden) td').forEach(td => {{
    if (td.querySelector('span[title]')) return; // skip transcript cells
    td.innerHTML = td.innerHTML.replace(re, '<mark class="search-hl">$1</mark>');
  }});

  if (countEl) countEl.textContent = totalMatch + ' row' + (totalMatch !== 1 ? 's' : '') + ' matched';
}}

// ===== Collapse/Expand =====
function toggleSection(sid) {{
  const body = document.getElementById('body-' + sid);
  const icon = document.getElementById('toggle-' + sid);
  if (!body) return;
  const collapsed = body.classList.toggle('collapsed');
  if (icon) icon.classList.toggle('collapsed', collapsed);
}}

function expandAll() {{
  document.querySelectorAll('.section-body').forEach(b => b.classList.remove('collapsed'));
  document.querySelectorAll('.toggle-icon').forEach(i => i.classList.remove('collapsed'));
}}

function collapseAll() {{
  document.querySelectorAll('.section-body').forEach(b => b.classList.add('collapsed'));
  document.querySelectorAll('.toggle-icon').forEach(i => i.classList.add('collapsed'));
}}

// ===== Copy TSV =====
function copyTable(sid) {{
  const tbl = document.getElementById('tbl-' + sid);
  if (!tbl) return;
  const rows = Array.from(tbl.querySelectorAll('tr'));
  const tsv = rows.map(r => Array.from(r.cells).map(c => c.textContent.trim().replace(/\\t/g, ' ')).join('\\t')).join('\\n');
  navigator.clipboard.writeText(tsv).then(() => {{
    showToast('Table copied as TSV');
    const btn = document.querySelector(`[onclick="copyTable('${{sid}}')"]`);
    if (btn) {{ btn.textContent = 'Copied!'; btn.classList.add('copied'); setTimeout(() => {{ btn.textContent = 'Copy TSV'; btn.classList.remove('copied'); }}, 1500); }}
  }}).catch(() => showToast('Copy failed'));
}}

function showToast(msg) {{
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2000);
}}

// ===== Dark Mode =====
function toggleTheme() {{
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  document.documentElement.setAttribute('data-theme', isDark ? '' : 'dark');
  const btn = document.getElementById('theme-btn');
  if (btn) btn.textContent = isDark ? 'Dark Mode' : 'Light Mode';
  localStorage.setItem('theme', isDark ? 'light' : 'dark');
}}

// ===== Active Nav =====
function updateActiveNav() {{
  const sections = document.querySelectorAll('.table-section');
  const navLinks = document.querySelectorAll('.nav-link');
  let current = '';
  sections.forEach(sec => {{
    const top = sec.getBoundingClientRect().top;
    if (top < 200) current = sec.id;
  }});
  navLinks.forEach(link => {{
    link.classList.toggle('active', link.getAttribute('href') === '#' + current);
  }});
}}

// ===== Init =====
(function() {{
  // Restore theme
  const saved = localStorage.getItem('theme');
  if (saved === 'dark') {{
    document.documentElement.setAttribute('data-theme', 'dark');
    const btn = document.getElementById('theme-btn');
    if (btn) btn.textContent = 'Light Mode';
  }}
  // Scroll spy
  window.addEventListener('scroll', updateActiveNav, {{passive: true}});
  updateActiveNav();
}})();
</script>
</body>
</html>'''


def main():
    print(f"Reading: {MD_FILE}")
    text = MD_FILE.read_text(encoding='utf-8')
    print("Parsing tables...")
    sections = parse_md_tables(text)
    for name, data in sections.items():
        print(f"  {name}: {len(data['headers'])} cols, {len(data['rows'])} rows")

    summary = sections.get('SUMMARY', {})
    kpis = compute_kpis(summary.get('rows', []), summary.get('headers', []))
    print(f"KPIs: spend=${kpis['total_spend']:,.0f}, leads={kpis['total_leads']}, scheds={kpis['total_scheds']}, avg_br={kpis['avg_br']:.1f}%")

    print("Generating HTML...")
    html = generate_html(sections, kpis)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(html, encoding='utf-8')
    size_kb = OUT_FILE.stat().st_size / 1024
    print(f"Written: {OUT_FILE}  ({size_kb:.0f} KB)")


if __name__ == '__main__':
    main()
