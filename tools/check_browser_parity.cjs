// The browser checker (prototype "Your letter" screen) must agree with the tested Python engine.
// Usage: node tools/check_browser_parity.cjs path/to/clean.jsonl
const fs = require('fs');
const html = fs.readFileSync(require('path').join(__dirname, '../prototype/index.html'), 'utf8');
const code = html.slice(html.indexOf('const TRY = {'), html.indexOf('const SAMPLE_LETTER'));
const inr = n => '₹' + n.toLocaleString('en-IN');
const esc = s => String(s);
const analyseLetter = new Function('inr', 'esc', code + '; return analyseLetter;')(inr, esc);
const rows = fs.readFileSync(process.argv[2], 'utf8').trim().split('\n').map(JSON.parse);
let ground = 0, amount = 0, quote = 0;
for (const r of rows) {
  const letter = r.enhanced_prompt || r.prompt || r.input;
  let gold = r.enhanced_completion || r.completion || r.output;
  if (typeof gold === 'string') gold = JSON.parse(gold.match(/\{[\s\S]*\}/)[0]);
  const res = analyseLetter(letter, '', true);
  ground += res.ground === gold.rejection_ground;
  amount += res.amount !== null && Math.abs(res.amount - Number(gold.claim_amount_inr)) < 1;
  quote += !!res.reason && letter.includes(res.reason);
}
const pct = x => (100 * x / rows.length).toFixed(1) + '%';
console.log(`browser engine on ${rows.length} letters: reason ${pct(ground)}, amount ${pct(amount)}, reason sentence found verbatim ${pct(quote)}`);
