# WS-G Reference: Spike HTML Structure

> Document skeleton extracted from spike. Shows layout, sidebar, header, KPI cards, and section pattern.
> Data rows stripped. Use as reference for HtmlRenderer output structure.

```html
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>{_CSS}</style>
  <script>{_JS}</script>
</head>
<body>
<div class="toast" id="toast">Copied</div>
<div class="layout">

<!-- Sidebar -->
<nav class="sidebar" aria-label="Sections">
  <div class="nav-section-label">Sections</div>
  <a href="#{section_id}" class="nav-link">{section_name}<span class="badge">{row_count}</span></a>
  <!-- repeat for each section -->
</nav>

<!-- Main -->
<main class="main-content">

  <!-- Report Header -->
  <div class="report-header">
    <div class="report-title">{business_name}</div>
    <div class="report-meta">
      Phone: {masked_phone} &nbsp;•&nbsp;
      Vertical: {vertical} &nbsp;•&nbsp;
      Generated: {timestamp}
      <!-- If offer_gid: -->
      &nbsp;•&nbsp; <a href="https://app.asana.com/0/0/{offer_gid}">View in Asana</a>
    </div>
    <div class="header-actions">
      <div class="search-wrap">
        <input type="text" id="global-search" placeholder="Search all tables..."
               oninput="onSearch(this.value)" autocomplete="off">
        <span class="search-clear" id="search-clear" onclick="clearSearch()">✕</span>
      </div>
      <span class="search-count" id="search-count"></span>
      <button class="btn" onclick="window.print()">Print</button>
      <button class="btn" id="theme-btn" onclick="toggleTheme()">Dark Mode</button>
      <button class="btn" onclick="expandAll()">Expand All</button>
      <button class="btn" onclick="collapseAll()">Collapse All</button>
    </div>
  </div>

  <!-- KPI Cards -->
  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{formatted_value}</div>
      <div class="kpi-sub">{subtitle}</div>
      <!-- Optional sparkline: -->
      <div class="kpi-sparkline">
        <svg width="140" height="36" viewBox="0 0 140 36" xmlns="http://www.w3.org/2000/svg">
          <polyline points="{points}" fill="none" stroke="var(--accent)"
                    stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/>
        </svg>
      </div>
    </div>
    <!-- repeat for each KPI card -->
  </div>

  <!-- Table Section Pattern -->
  <section id="{section_id}" class="table-section">
    <div class="section-header" onclick="toggleSection('{section_id}')">
      <h2>{section_name} <span class="badge">{row_count} rows</span></h2>
      <div class="section-controls">
        <button class="copy-btn" onclick="event.stopPropagation();copyTable('{section_id}')">Copy TSV</button>
        <span class="toggle-icon {collapsed_class}" id="toggle-{section_id}">▼</span>
      </div>
    </div>
    <div class="section-subtitle">{subtitle_text}</div>
    <div class="section-body {collapsed_class}" id="body-{section_id}">
      <div class="table-scroll">
        <table id="tbl-{section_id}" class="data-table">
          <thead><tr>
            <th onclick="sortTable('{section_id}',0)" title="{tooltip}">
              {display_label}<span class="sort-icon"></span>
            </th>
            <!-- repeat for each column -->
          </tr></thead>
          <tbody>
            <tr>
              <td class="{align_class} {cond_format_class}">{formatted_value}</td>
              <!-- repeat for each column -->
            </tr>
            <!-- repeat for each row -->
          </tbody>
        </table>
      </div>
      <!-- Truncation note if applicable: -->
      <p class="truncation-note">Showing {display_count} of {total_count} rows</p>
    </div>
    <!-- Embedded full data for Copy TSV (all columns): -->
    <script type="application/json" id="data-{section_id}">[{full_row_json}]</script>
  </section>

  <!-- Empty Section Pattern -->
  <section id="{section_id}" class="table-section">
    <div class="section-header" onclick="toggleSection('{section_id}')">
      <h2>{section_name}</h2>
      <div class="section-controls">
        <span class="toggle-icon" id="toggle-{section_id}">▼</span>
      </div>
    </div>
    <div class="section-body" id="body-{section_id}">
      <p class="empty">{message}</p>
    </div>
  </section>

  <!-- Footer -->
  <footer class="report-footer">
    <span class="footer-item"><strong>{key}:</strong> {value}</span>
    <!-- repeat for each footer item -->
  </footer>

</main>
</div>
</body>
</html>
```

## Key Structural Notes

1. **Toast element** is placed at body root level (above layout div)
2. **Sidebar** comes before `<main>` in the flex layout
3. **Section subtitle** is OUTSIDE the section-body (visible even when collapsed)
4. **JSON data embed** is at the section level, outside section-body, for Copy TSV
5. **Default collapsed**: All sections start with `class="collapsed"` on section-body EXCEPT the ones that should be expanded by default (SUMMARY, BY WEEK per spec)
6. **event.stopPropagation()** on Copy TSV button prevents triggering the section toggle
