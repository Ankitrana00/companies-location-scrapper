// Interactive review of uncertain matches (weak / out_of_area).
// Usage:
//   node review.js --dir C:\path\to\data jaipur      (single city)
//   node review.js --dir C:\path\to\data all         (every *_matched.json in dir)
// Keys: [y] keep pin  [n] reject  [s] skip (decide later)  [q] quit (saves)
// Decisions are saved into the matched.json after every answer (crash-safe).
// After reviewing, re-run build_excel_trusted.py - verified rows join the Excel.
const fs = require('fs');
const path = require('path');
const readline = require('readline');

const args = process.argv.slice(2);
let dir = __dirname, target = null;
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--dir') dir = args[++i];
  else target = args[i];
}
if (!target) { console.error('Usage: node review.js [--dir <dataDir>] <city|all>'); process.exit(1); }

function dataFiles() {
  const files = fs.readdirSync(dir).filter(f => f.endsWith('_matched.json'));
  if (fs.existsSync(path.join(dir, 'matched.json')) && !files.includes('jaipur_matched.json')) {
    files.push('matched.json'); // legacy Jaipur name
  }
  return files.sort();
}

function cityLabel(file) {
  return file === 'matched.json' ? 'jaipur' : file.replace('_matched.json', '');
}

const REVIEWABLE = new Set(['weak', 'out_of_area']);
let reviewed = 0, kept = 0, rejected = 0, skipped = 0;

async function reviewCity(file) {
  const p = path.join(dir, file);
  const data = JSON.parse(fs.readFileSync(p, 'utf8'));
  const rows = data.map((o, i) => ({ o, i })).filter(({ o }) => REVIEWABLE.has(o.status));
  if (!rows.length) { console.log(`\n[${cityLabel(file)}] nothing to review.`); return; }
  console.log(`\n=== ${cityLabel(file)}: ${rows.length} rows to review ===`);
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  const ask = q => new Promise(res => rl.question(q, a => res(a.trim().toLowerCase())));
  for (const { o } of rows) {
    console.log('\n' + '-'.repeat(70));
    console.log('YOUR LIST : ' + o.name);
    console.log('GOOGLE    : ' + (o.matchTitle || '(none)'));
    console.log('ADDRESS   : ' + (o.address || '(none)').slice(0, 90));
    console.log('PIN       : ' + (o.lat || '?') + ', ' + (o.lng || '?') +
      (o.status === 'out_of_area' ? '   [OUTSIDE CITY BOUNDS]' : '') +
      '   score ' + o.score);
    if (o.mapsLink) console.log('MAPS      : ' + o.mapsLink.slice(0, 110));
    let done = false;
    while (!done) {
      const a = await ask('[y] keep / [n] reject / [s] skip / [q] quit > ');
      if (a === 'y') { o.status = 'verified'; kept++; done = true; }
      else if (a === 'n') { o.status = 'rejected'; rejected++; done = true; }
      else if (a === 's') { skipped++; done = true; }
      else if (a === 'q') { rl.close(); fs.writeFileSync(p, JSON.stringify(data, null, 1)); console.log('saved & quit.'); return; }
      else console.log('  y / n / s / q');
    }
    reviewed++;
    fs.writeFileSync(p, JSON.stringify(data, null, 1)); // save after every answer
  }
  rl.close();
}

(async () => {
  const files = target === 'all' ? dataFiles() : [target === 'jaipur' ? (fs.existsSync(path.join(dir, 'jaipur_matched.json')) ? 'jaipur_matched.json' : 'matched.json') : target + '_matched.json'];
  for (const f of files) {
    if (!fs.existsSync(path.join(dir, f))) { console.error('missing: ' + f); continue; }
    await reviewCity(f);
  }
  console.log('\n=== summary ===');
  console.log('reviewed:', reviewed, '| kept:', kept, '| rejected:', rejected, '| skipped:', skipped);
  console.log('now re-run: py build_excel_trusted.py  (verified rows join the Excel)');
})();
