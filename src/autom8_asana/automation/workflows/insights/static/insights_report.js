// ===== Sort =====
var sortState = {};

function sortTable(sid, colIdx) {
  var tbl = document.getElementById('tbl-' + sid);
  if (!tbl) return;
  var th = tbl.querySelectorAll('thead th');
  var key = sid + '-' + colIdx;
  var asc = sortState[key] !== 'asc';
  sortState[key] = asc ? 'asc' : 'desc';
  th.forEach(function(h, i) {
    h.classList.remove('sort-asc', 'sort-desc');
    if (i === colIdx) h.classList.add(asc ? 'sort-asc' : 'sort-desc');
  });
  var tbody = tbl.querySelector('tbody');
  var rows = Array.from(tbody.querySelectorAll('tr'));
  rows.sort(function(a, b) {
    var aCell = (a.cells[colIdx] && a.cells[colIdx].textContent || '').trim();
    var bCell = (b.cells[colIdx] && b.cells[colIdx].textContent || '').trim();
    var aNum = parseFloat(aCell.replace(/[^0-9.\-]/g, ''));
    var bNum = parseFloat(bCell.replace(/[^0-9.\-]/g, ''));
    var cmp = 0;
    if (!isNaN(aNum) && !isNaN(bNum)) { cmp = aNum - bNum; }
    else { cmp = aCell.localeCompare(bCell, undefined, {numeric: true}); }
    return asc ? cmp : -cmp;
  });
  rows.forEach(function(r) { tbody.appendChild(r); });
}

// ===== Search =====
var searchTimeout = null;

function onSearch(val) {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(function() { doSearch(val); }, 80);
  var clear = document.getElementById('search-clear');
  if (clear) clear.style.display = val ? 'block' : 'none';
}

function clearSearch() {
  var inp = document.getElementById('global-search');
  if (inp) { inp.value = ''; doSearch(''); }
  var clear = document.getElementById('search-clear');
  if (clear) clear.style.display = 'none';
}

function doSearch(query) {
  var q = query.trim().toLowerCase();
  var countEl = document.getElementById('search-count');
  if (!q) {
    document.querySelectorAll('mark.search-hl').forEach(function(m) { m.outerHTML = m.innerHTML; });
    document.querySelectorAll('tr.search-hidden').forEach(function(r) { r.classList.remove('search-hidden'); });
    if (countEl) countEl.textContent = '';
    return;
  }
  var totalMatch = 0;
  document.querySelectorAll('.data-table tbody tr').forEach(function(row) {
    var text = row.textContent.toLowerCase();
    if (text.includes(q)) { row.classList.remove('search-hidden'); totalMatch++; }
    else { row.classList.add('search-hidden'); }
  });
  document.querySelectorAll('mark.search-hl').forEach(function(m) { m.outerHTML = m.innerHTML; });
  var re = new RegExp('(' + q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
  document.querySelectorAll('.data-table tbody tr:not(.search-hidden) td').forEach(function(td) {
    if (td.querySelector('span[title]')) return;
    td.innerHTML = td.innerHTML.replace(re, '<mark class="search-hl">$1</mark>');
  });
  if (countEl) countEl.textContent = totalMatch + ' row' + (totalMatch !== 1 ? 's' : '') + ' matched';
}

// ===== Collapse/Expand =====
function toggleSection(sid) {
  var body = document.getElementById('body-' + sid);
  var icon = document.getElementById('toggle-' + sid);
  if (!body) return;
  var collapsed = body.classList.toggle('collapsed');
  if (icon) icon.classList.toggle('collapsed', collapsed);
}

function expandAll() {
  document.querySelectorAll('.section-body').forEach(function(b) { b.classList.remove('collapsed'); });
  document.querySelectorAll('.toggle-icon').forEach(function(i) { i.classList.remove('collapsed'); });
}

function collapseAll() {
  document.querySelectorAll('.section-body').forEach(function(b) { b.classList.add('collapsed'); });
  document.querySelectorAll('.toggle-icon').forEach(function(i) { i.classList.add('collapsed'); });
}

// ===== Copy TSV =====
function copyTable(sid) {
  var dataEl = document.getElementById('data-' + sid);
  if (!dataEl) return;
  try {
    var rows = JSON.parse(dataEl.textContent);
    if (!rows.length) return;
    var headers = Object.keys(rows[0]);
    var tsv = [headers.join('\t')]
      .concat(rows.map(function(r) { return headers.map(function(h) { return String(r[h] != null ? r[h] : ''); }).join('\t'); }))
      .join('\n');
    navigator.clipboard.writeText(tsv).then(function() {
      showToast('Table copied as TSV (' + rows.length + ' rows, ' + headers.length + ' columns)');
      var btn = document.querySelector('[onclick="copyTable(\'' + sid + '\')"');
      if (btn) { btn.textContent = 'Copied!'; btn.classList.add('copied'); setTimeout(function() { btn.textContent = 'Copy TSV'; btn.classList.remove('copied'); }, 1500); }
    }).catch(function() { showToast('Copy failed'); });
  } catch(e) { showToast('Copy failed'); }
}

function showToast(msg) {
  var t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(function() { t.classList.remove('show'); }, 2000);
}

// ===== Theme Toggle =====
function toggleTheme() {
  var html = document.documentElement;
  var current = html.getAttribute('data-theme');
  var next = current === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  var btn = document.getElementById('theme-btn');
  if (btn) btn.textContent = next === 'dark' ? 'Light Mode' : 'Dark Mode';
  try { localStorage.setItem('theme', next); } catch(e) {}
}

// ===== Active Nav (Scroll Spy) =====
function updateActiveNav() {
  var sections = document.querySelectorAll('.table-section');
  var navLinks = document.querySelectorAll('.nav-link');
  var current = '';
  sections.forEach(function(sec) {
    var top = sec.getBoundingClientRect().top;
    if (top < 200) current = sec.id;
  });
  navLinks.forEach(function(link) {
    link.classList.toggle('active', link.getAttribute('href') === '#' + current);
  });
}

// ===== Init =====
(function() {
  var saved = typeof localStorage !== 'undefined' ? localStorage.getItem('theme') : null;
  if (saved) {
    document.documentElement.setAttribute('data-theme', saved);
  } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    document.documentElement.setAttribute('data-theme', 'dark');
  }
  var btn = document.getElementById('theme-btn');
  var theme = document.documentElement.getAttribute('data-theme');
  if (btn) btn.textContent = theme === 'dark' ? 'Light Mode' : 'Dark Mode';
  window.addEventListener('scroll', updateActiveNav, {passive: true});
  updateActiveNav();
})();
