/**
 * Toy Ticker sightings: the write and read path for the toy map (sightings.html).
 *
 * Lives in the "Toy Ticker Map" Google Sheet: Extensions > Apps Script, paste this file, then
 * Deploy > New deployment > Web app, Execute as: Me, Who has access: Anyone. Put the /exec URL in
 * data/sightings.json as "endpoint". After editing this script, Deploy > Manage deployments > edit > New version
 * (the URL stays the same).
 *
 * POST (form-encoded store_id, store_name, address, lat, lon, series, toys, out): appends one row.
 * GET: the last WINDOW_DAYS of reports as CSV, header row first.
 */
const SHEET = 'Sheet1';
const HEADER = ['timestamp', 'store_id', 'store_name', 'address', 'lat', 'lon', 'series', 'toys', 'out'];
const WINDOW_DAYS = 30;        // GET returns this much; the page shows its own window (14 days) within it
const MAX_PER_MINUTE = 30;     // all visitors together; stops a flood of junk rows

function doPost(e) {
  const p = (e && e.parameter) || {};
  const lat = Number(p.lat), lon = Number(p.lon);
  const ok = /^osm:[nwr]\d{1,15}$/.test(p.store_id || '')
    && isFinite(lat) && isFinite(lon) && Math.abs(lat) <= 90 && Math.abs(lon) <= 180
    && /^[a-z0-9-]{1,60}$/.test(p.series || '')
    && /^[a-z0-9,-]{0,600}$/.test(p.toys || '')
    && (p.toys || p.out === 'yes');
  if (!ok) return text_('bad request');

  const cache = CacheService.getScriptCache();
  const key = 'n' + Math.floor(Date.now() / 60000);
  const n = Number(cache.get(key) || 0);
  if (n >= MAX_PER_MINUTE) return text_('busy');
  cache.put(key, String(n + 1), 120);

  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const sh = sheet_();
    sh.appendRow([new Date(), p.store_id, safe_(p.store_name, 80), safe_(p.address, 160), lat, lon,
                  p.series, p.toys || '', p.out === 'yes' ? 'yes' : 'no']);
  } finally {
    lock.releaseLock();
  }
  cache.remove('csv');
  return text_('ok');
}

function doGet() {
  const cache = CacheService.getScriptCache();
  const hit = cache.get('csv');
  if (hit) return csv_(hit);
  const rows = sheet_().getDataRange().getValues().slice(1);
  const since = Date.now() - WINDOW_DAYS * 864e5;
  const lines = [HEADER.join(',')];
  for (const r of rows) {
    const ts = r[0] instanceof Date ? r[0] : new Date(r[0]);
    if (isNaN(ts) || ts.getTime() < since || !r[1]) continue;
    lines.push([ts.toISOString()].concat(r.slice(1, HEADER.length)).map(cell_).join(','));
  }
  const out = lines.join('\n');
  if (out.length < 90000) cache.put('csv', out, 60);   // cache values max out at 100 KB
  return csv_(out);
}

function sheet_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName(SHEET) || ss.insertSheet(SHEET);
  if (sh.getLastRow() === 0) sh.appendRow(HEADER);
  return sh;
}
// Plain text only, and never a formula: a leading = + - @ would run as one in the sheet.
function safe_(s, max) {
  s = String(s || '').replace(/[\u0000-\u001f]/g, ' ').trim().slice(0, max);
  return /^[=+\-@]/.test(s) ? "'" + s : s;
}
function cell_(v) {
  const s = String(v == null ? '' : v);
  return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}
function text_(s) { return ContentService.createTextOutput(s).setMimeType(ContentService.MimeType.TEXT); }
function csv_(s) { return ContentService.createTextOutput(s).setMimeType(ContentService.MimeType.CSV); }
