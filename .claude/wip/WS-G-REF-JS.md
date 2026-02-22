# WS-G Reference: Spike JavaScript

> Extracted from spike HTML lines 1508-1676. Use as reference for _JS constant.
> Adapt IDs and function signatures to match the production renderer's HTML structure.

```javascript
// ===== Sort =====
const sortState = {};

function sortTable(sid, colIdx) {
  const tbl = document.getElementById('tbl-' + sid);
  if (!tbl) return;
  const th = tbl.querySelectorAll('thead th');
  const key = sid + '-' + colIdx;
  const asc = sortState[key] !== 'asc';
  sortState[key] = asc ? 'asc' : 'desc';

  th.forEach((h, i) => {
    h.classList.remove('sort-asc', 'sort-desc');
    if (i === colIdx) h.classList.add(asc ? 'sort-asc' : 'sort-desc');
  });

  const tbody = tbl.querySelector('tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  rows.sort((a, b) => {
    const aCell = a.cells[colIdx]?.textContent?.trim() ?? '';
    const bCell = b.cells[colIdx]?.textContent?.trim() ?? '';
    const aNum = parseFloat(aCell.replace(/[^0-9.\-]/g, ''));
    const bNum = parseFloat(bCell.replace(/[^0-9.\-]/g, ''));
    let cmp = 0;
    if (!isNaN(aNum) && !isNaN(bNum)) {
      cmp = aNum - bNum;
    } else {
      cmp = aCell.localeCompare(bCell, undefined, {numeric: true});
    }
    return asc ? cmp : -cmp;
  });
  rows.forEach(r => tbody.appendChild(r));
}

// ===== Search =====
let searchTimeout = null;

function onSearch(val) {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => doSearch(val), 80);
  const clear = document.getElementById('search-clear');
  if (clear) clear.style.display = val ? 'block' : 'none';
}

function clearSearch() {
  const inp = document.getElementById('global-search');
  if (inp) { inp.value = ''; doSearch(''); }
  const clear = document.getElementById('search-clear');
  if (clear) clear.style.display = 'none';
}

function doSearch(query) {
  const q = query.trim().toLowerCase();
  const countEl = document.getElementById('search-count');
  if (!q) {
    document.querySelectorAll('mark.search-hl').forEach(m => {
      m.outerHTML = m.innerHTML;
    });
    document.querySelectorAll('tr.search-hidden').forEach(r => r.classList.remove('search-hidden'));
    if (countEl) countEl.textContent = '';
    return;
  }

  let totalMatch = 0;
  document.querySelectorAll('.data-table tbody tr').forEach(row => {
    const text = row.textContent.toLowerCase();
    if (text.includes(q)) {
      row.classList.remove('search-hidden');
      totalMatch++;
    } else {
      row.classList.add('search-hidden');
    }
  });

  document.querySelectorAll('mark.search-hl').forEach(m => {
    m.outerHTML = m.innerHTML;
  });
  const re = new RegExp('(' + q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
  document.querySelectorAll('.data-table tbody tr:not(.search-hidden) td').forEach(td => {
    if (td.querySelector('span[title]')) return;
    td.innerHTML = td.innerHTML.replace(re, '<mark class="search-hl">$1</mark>');
  });

  if (countEl) countEl.textContent = totalMatch + ' row' + (totalMatch !== 1 ? 's' : '') + ' matched';
}

// ===== Collapse/Expand =====
function toggleSection(sid) {
  const body = document.getElementById('body-' + sid);
  const icon = document.getElementById('toggle-' + sid);
  if (!body) return;
  const collapsed = body.classList.toggle('collapsed');
  if (icon) icon.classList.toggle('collapsed', collapsed);
}

function expandAll() {
  document.querySelectorAll('.section-body').forEach(b => b.classList.remove('collapsed'));
  document.querySelectorAll('.toggle-icon').forEach(i => i.classList.remove('collapsed'));
}

function collapseAll() {
  document.querySelectorAll('.section-body').forEach(b => b.classList.add('collapsed'));
  document.querySelectorAll('.toggle-icon').forEach(i => i.classList.add('collapsed'));
}

// ===== Copy TSV =====
function copyTable(sid) {
  // Read from embedded JSON data (all columns, not just visible)
  const dataEl = document.getElementById('data-' + sid);
  if (!dataEl) return;
  try {
    const rows = JSON.parse(dataEl.textContent);
    if (!rows.length) return;
    const headers = Object.keys(rows[0]);
    const tsv = [headers.join('\t')]
      .concat(rows.map(r => headers.map(h => String(r[h] ?? '')).join('\t')))
      .join('\n');
    navigator.clipboard.writeText(tsv).then(() => {
      showToast('Table copied as TSV (' + rows.length + ' rows, ' + headers.length + ' columns)');
      const btn = document.querySelector(`[onclick="copyTable('${sid}')"]`);
      if (btn) { btn.textContent = 'Copied!'; btn.classList.add('copied'); setTimeout(() => { btn.textContent = 'Copy TSV'; btn.classList.remove('copied'); }, 1500); }
    }).catch(() => showToast('Copy failed'));
  } catch(e) { showToast('Copy failed'); }
}

function showToast(msg) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2000);
}

// ===== Theme Toggle =====
function toggleTheme() {
  const html = document.documentElement;
  const current = html.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  const btn = document.getElementById('theme-btn');
  if (btn) btn.textContent = next === 'dark' ? 'Light Mode' : 'Dark Mode';
  try { localStorage.setItem('theme', next); } catch(e) {}
}

// ===== Active Nav (Scroll Spy) =====
function updateActiveNav() {
  const sections = document.querySelectorAll('.table-section');
  const navLinks = document.querySelectorAll('.nav-link');
  let current = '';
  sections.forEach(sec => {
    const top = sec.getBoundingClientRect().top;
    if (top < 200) current = sec.id;
  });
  navLinks.forEach(link => {
    link.classList.toggle('active', link.getAttribute('href') === '#' + current);
  });
}

// ===== Init =====
(function() {
  // Detect system preference, apply saved theme
  const saved = typeof localStorage !== 'undefined' ? localStorage.getItem('theme') : null;
  if (saved) {
    document.documentElement.setAttribute('data-theme', saved);
  } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    document.documentElement.setAttribute('data-theme', 'dark');
  }
  const btn = document.getElementById('theme-btn');
  const theme = document.documentElement.getAttribute('data-theme');
  if (btn) btn.textContent = theme === 'dark' ? 'Light Mode' : 'Dark Mode';

  // Scroll spy
  window.addEventListener('scroll', updateActiveNav, {passive: true});
  updateActiveNav();
})();
```

## Key Adaptations for Production

1. **copyTable**: Reads from `<script type="application/json" id="data-{sid}">` -- NOT from visible table DOM. This ensures Copy TSV exports ALL columns including hidden ones.
2. **Theme init**: Uses `prefers-color-scheme` as default, `localStorage` for user override.
3. **IDs**: Section IDs use slugified names (`tbl-{slug}`, `body-{slug}`, `toggle-{slug}`, `data-{slug}`).
