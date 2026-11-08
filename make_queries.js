// Generate queries file from a names file.
// Usage: node make_queries.js <city>
// Reads <city>_names.txt, writes <city>_queries.txt with "Name, <City>" per line.
const fs = require('fs');
const path = require('path');
const city = process.argv[2];
if (!city) { console.error('Usage: node make_queries.js <city>'); process.exit(1); }
const file = path.join(__dirname, city + '_names.txt');
if (!fs.existsSync(file)) { console.error('Missing ' + file); process.exit(1); }
const names = fs.readFileSync(file, 'utf8').split(/\r?\n/).map(s => s.trim()).filter(s => /[a-zA-Z]{2,}/.test(s));
const seen = new Set(); const queries = [];
for (const n of names) {
  const k = n.toLowerCase();
  if (seen.has(k)) continue; seen.add(k);
  queries.push(n + ', ' + city.charAt(0).toUpperCase() + city.slice(1));
}
fs.writeFileSync(path.join(__dirname, city + '_queries.txt'), queries.join('\n') + '\n');
console.log('usable names:', names.length, '| unique queries:', queries.length, '->', city + '_queries.txt');
