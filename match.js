// Match scraped Google Maps results back to the input company names.
const fs = require('fs');
const path = require('path');
const DIR = __dirname;
// usage: node match.js [namesFile] [resultsFile] [outJson] [latMin latMax lngMin lngMax] [cityLabel]
const A = process.argv.slice(2);
const NAMES_FILE = A[0] || 'names.txt';
const RESULTS_FILE = A[1] || 'results.csv';
const OUT_FILE = A[2] || 'matched.json';
const [LA_MIN, LA_MAX, LN_MIN, LN_MAX] = A.length >= 7 ? A.slice(3, 7).map(Number) : [26.4, 27.4, 75.2, 76.4];
const CITY = A[7] || 'Jaipur';

// --- parse CSV with quoted fields ---
function parseCSV(text) {
  const rows = []; let row = []; let field = ''; let inQ = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQ) {
      if (c === '"') { if (text[i + 1] === '"') { field += '"'; i++; } else inQ = false; }
      else field += c;
    } else if (c === '"') inQ = true;
    else if (c === ',') { row.push(field); field = ''; }
    else if (c === '\n') { row.push(field); rows.push(row); row = []; field = ''; }
    else if (c !== '\r') field += c;
  }
  if (field.length || row.length) { row.push(field); rows.push(row); }
  return rows;
}

// generous district bounds; excludes Delhi/Mumbai/other cities clearly
const IN_JAIPUR = (lat, lng) => lat >= LA_MIN && lat <= LA_MAX && lng >= LN_MIN && lng <= LN_MAX;
// Delhi's box unavoidably contains Gurugram/Noida/Ghaziabad, so also require
// the address to carry city evidence: "Delhi"/"New Delhi" or a 110xxx pincode
function geoOk(r) {
  const la = parseFloat(get(r, 'latitude')), ln = parseFloat(get(r, 'longitude'));
  if (isNaN(la) || isNaN(ln)) return null;
  if (!IN_JAIPUR(la, ln)) return false;
  if (CITY === 'Delhi') {
    const addr = get(r, 'address') + ' ' + get(r, 'complete_address');
    if (!(/delhi/i.test(addr) || /\b110\d{3}\b/.test(addr))) return false;
  }
  return true;
}

const STOP = new Set(['pvt','private','ltd','limited','llp','llc','inc','opc','co','corp','corporation','company','jaipur','lucknow','india','the','a','an','and','of']);
function norm(s) {
  return (s || '').toLowerCase()
    .replace(/[™®©°•]/g, ' ')
    .replace(/&/g, ' and ')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim().split(/\s+/)
    .filter(w => w && !STOP.has(w)).join(' ');
}
function bigrams(s) { const r = new Set(); for (let i = 0; i < s.length - 1; i++) r.add(s.slice(i, i + 2)); return r; }
function dice(a, b) {
  if (!a || !b) return 0; if (a === b) return 1;
  const A = bigrams(a), B = bigrams(b); let inter = 0;
  for (const g of A) if (B.has(g)) inter++;
  return 2 * inter / (A.size + B.size);
}
const GENERIC = new Set(['software','softwares','technologies','technology','tech','solutions','solution','services','service','info','infosoft','infotech','infotechs','systems','system','web','webdev','app','apps','digital','it','development','developers','developer','consultancy','consulting','labs','studio','outsource','outsourcing','ventures','enterprises','enterprise','global','technosys','softtech','softech','infosystems','technocrats','india']);
function distinctiveTokens(s) {
  return norm(s).split(' ').filter(w => w.length >= 3 && !GENERIC.has(w));
}
function compact(s) { return norm(s).replace(/ /g, ''); }
function score(query, title) {
  const nq = norm(query), nt = norm(title);
  if (!nq || !nt) return 0;
  if (nq === nt) return 1;
  let s = dice(nq, nt);
  if (nq.includes(nt) || nt.includes(nq)) s = Math.max(s, 0.82);
  const cq = compact(query), ct = compact(title);
  if (cq && ct && (cq.includes(ct) || ct.includes(cq))) s = Math.max(s, 0.82);
  // sharing a distinctive company word alone only earns the "review" band
  const dq = distinctiveTokens(query), dt = distinctiveTokens(title);
  const sharedDistinctive = dq.some(w => dt.includes(w));
  if (sharedDistinctive) s = Math.max(s, 0.68);
  // generic words (Infotech/Technologies...) must not carry the match alone:
  // if the query has distinctive words and none of them appear in the title,
  // the match can never be trusted above the review band
  if (dq.length && !sharedDistinctive && !(cq && ct && (cq.includes(ct) || ct.includes(cq)))) s = Math.min(s, 0.68);
  return s;
}

const names = fs.readFileSync(path.join(DIR, NAMES_FILE), 'utf8').split(/\r?\n/).map(s => s.trim()).filter(Boolean);
const csvText = fs.readFileSync(path.join(DIR, RESULTS_FILE), 'utf8');
const rows = parseCSV(csvText);
const header = rows[0];
const idx = Object.fromEntries(header.map((h, i) => [h, i]));
const get = (r, k) => (idx[k] !== undefined ? (r[idx[k]] || '').trim() : '');

// dedupe results by place key, keep the row with the most data
const byKey = new Map();
for (const r of rows.slice(1)) {
  if (r.length < 5) continue;
  const key = get(r, 'place_id') || get(r, 'cid') || get(r, 'data_id') || get(r, 'link');
  const filled = ['title','address','latitude','longitude','website','phone'].filter(k => get(r, k)).length;
  const prev = byKey.get(key);
  if (!prev || prev.filled < filled) byKey.set(key, { r, filled });
}
const results = [...byKey.values()].map(v => v.r);
console.log('input names:', names.length, '| raw rows:', rows.length - 1, '| unique places:', results.length);

// score matrix — geography-aware: all companies are stated to be in Jaipur,
// so an in-bounds candidate beats an equally-good-name out-of-bounds one
const S = names.map(n => results.map(r => {
  const base = score(n, get(r, 'title'));
  if (base === 0) return 0;
  const g = geoOk(r);
  if (g === false) return base * 0.55;
  // bonus only lifts candidates already above the review band (0.7);
  // capped/generic-word matches must stay in the review band
  if (g === true && base > 0.7) return Math.min(1, base + 0.06);
  return base;
}));
const usedRes = new Array(results.length).fill(false);
const assign = new Array(names.length).fill(null);

// pass 1: mutual best
for (let qi = 0; qi < names.length; qi++) {
  let bi = -1, bs = 0;
  for (let ri = 0; ri < results.length; ri++) if (S[qi][ri] > bs) { bs = S[qi][ri]; bi = ri; }
  if (bi >= 0 && bs >= 0.55) {
    let bq = -1, bs2 = 0;
    for (let qj = 0; qj < names.length; qj++) if (S[qj][bi] > bs2) { bs2 = S[qj][bi]; bq = qj; }
    if (bq === qi) { assign[qi] = { ri: bi, sc: bs }; usedRes[bi] = true; }
  }
}
// pass 2: greedy
const qOrder = names.map((_, qi) => qi).filter(qi => !assign[qi])
  .sort((a, b) => Math.max(...S[b]) - Math.max(...S[a]));
for (const qi of qOrder) {
  let bi = -1, bs = 0;
  for (let ri = 0; ri < results.length; ri++) if (!usedRes[ri] && S[qi][ri] > bs) { bs = S[qi][ri]; bi = ri; }
  if (bi >= 0 && bs >= 0.55) { assign[qi] = { ri: bi, sc: bs }; usedRes[bi] = true; }
}
// pass 3: duplicates (query variants of an already-matched place)
for (let qi = 0; qi < names.length; qi++) {
  if (assign[qi]) continue;
  let bi = -1, bs = 0;
  for (let ri = 0; ri < results.length; ri++) if (S[qi][ri] > bs) { bs = S[qi][ri]; bi = ri; }
  if (bi >= 0 && bs >= 0.7) {
    const owner = assign.findIndex(a => a && a.ri === bi);
    assign[qi] = { ri: bi, sc: bs, dupOf: owner };
  }
}

function statusOf(a) {
  if (!a) return 'not_found';
  if (a.dupOf !== undefined) return 'duplicate';
  if (geoOk(results[a.ri]) === false) return 'out_of_area';
  if (a.sc >= 0.9) return 'high';
  if (a.sc >= 0.7) return 'good';
  return 'weak';
}

function readableAddress(r) {
  const plain = get(r, 'address');
  if (plain && !plain.startsWith('{')) return plain;
  try {
    const c = JSON.parse(get(r, 'complete_address') || '{}');
    return [c.street, c.borough, c.city, c.state, c.postal_code].filter(Boolean).join(', ');
  } catch { return plain || get(r, 'complete_address'); }
}
const out = names.map((name, qi) => {
  const a = assign[qi];
  const st = statusOf(a);
  const base = { name, status: st, score: a ? +a.sc.toFixed(3) : 0 };
  if (a) {
    const r = results[a.ri];
    Object.assign(base, {
      matchTitle: get(r, 'title'),
      address: readableAddress(r),
      lat: get(r, 'latitude'), lng: get(r, 'longitude'),
      website: get(r, 'website'), phone: get(r, 'phone'),
      category: get(r, 'category'),
      rating: get(r, 'review_rating'), reviews: get(r, 'review_count'),
      mapsLink: get(r, 'link'),
    });
    if (a.dupOf !== undefined) base.dupOfName = names[a.dupOf];
  }
  return base;
});

const stats = {};
for (const o of out) stats[o.status] = (stats[o.status] || 0) + 1;
console.log('match stats:', JSON.stringify(stats));

const noCoords = out.filter(o => o.status !== 'not_found' && (!o.lat || !o.lng));
console.log('matched but missing coords:', noCoords.length);

fs.writeFileSync(path.join(DIR, OUT_FILE), JSON.stringify(out, null, 1));
console.log('\n--- weak / not found (review these) ---');
for (const o of out) if (o.status === 'weak' || o.status === 'not_found') console.log(o.status.padEnd(10), '|', o.name.slice(0, 60), '|', (o.matchTitle || '').slice(0, 50));
