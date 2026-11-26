// Browser tests for the prototype, plus an axe-core accessibility audit (WCAG 2.2 AA).
// Run:  npm i playwright@1.63.0 axe-core@4.10.2 && npx playwright install chromium && node tests/e2e/prototype.e2e.cjs
const { chromium } = require('playwright');
const path = require('path');
const assert = require('assert');

const AXE = require.resolve('axe-core/axe.min.js');
const PAGE = 'file://' + path.resolve(__dirname, '../../prototype/index.html');
const SCREENS = ['home', 'try', 'upload', 'analyse', 'verdict', 'letter', 'track'];

async function audit(page, label, failures) {
  await page.addScriptTag({ path: AXE });
  const res = await page.evaluate(() => axe.run(document, {
    runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'] },
  }));
  for (const v of res.violations.filter(v => ['serious', 'critical'].includes(v.impact))) {
    failures.push(`${label}: ${v.id} (${v.impact}) x${v.nodes.length}: ${v.nodes[0].target.join(' ')}`);
  }
}

(async () => {
  const browser = await chromium.launch();
  const failures = [];
  for (const [w, h, name] of [[1280, 800, 'laptop'], [390, 844, 'phone']]) {
    for (const scheme of ['light', 'dark']) {
      const page = await browser.newPage({ viewport: { width: w, height: h }, colorScheme: scheme });
      const errors = [];
      page.on('pageerror', e => errors.push(e.message));
      await page.goto(PAGE);
      for (const s of SCREENS) {
        await page.evaluate(x => { location.hash = x; }, s);
        await page.waitForTimeout(s === 'analyse' ? 4800 : 250);
        const sw = await page.evaluate(() => document.documentElement.scrollWidth);
        assert.ok(sw <= w, `${name}/${scheme}/${s}: page scrolls sideways (${sw}px > ${w}px)`);
        await audit(page, `${name}/${scheme}/${s}`, failures);
      }
      assert.deepStrictEqual(errors, [], `${name}/${scheme}: script errors`);
      await page.close();
    }
  }

  // Flow: the analyse button stays locked until a rejection letter is added.
  const page = await browser.newPage();
  await page.goto(PAGE + '#upload');
  assert.strictEqual(await page.getAttribute('a.btn[href="#analyse"]', 'aria-disabled'), 'true');
  await page.setInputFiles('#f-rej', { name: 'letter.pdf', mimeType: 'application/pdf', buffer: Buffer.from('x') });
  assert.strictEqual(await page.getAttribute('a.btn[href="#analyse"]', 'aria-disabled'), 'false');
  assert.ok((await page.textContent('main')).includes('letter.pdf'));

  // Flow: verdict sources open, and the language switch translates the verdict.
  await page.evaluate(() => { location.hash = 'verdict'; });
  await page.click('.chip >> nth=0');
  assert.ok(await page.isVisible('#drawer'));
  await page.click('#close');
  await page.click('#lang-hi');
  assert.match(await page.textContent('h1'), /मज़बूत/);
  await page.click('#lang-ta');
  assert.match(await page.textContent('h1'), /வலுவான/);
  await page.click('#lang-en');

  // Three sample cases: real precedents on case 1, a strong rule-based case 2, an honest "Fair" case 3.
  assert.ok((await page.textContent('main')).includes('LI/BK-10/05-06'));
  await page.click('[data-case="1"]');
  assert.match(await page.textContent('h1'), /Strong case/);
  assert.ok((await page.textContent('main')).includes('36-month maximum'));
  await page.click('[data-case="2"]');
  assert.match(await page.textContent('h1'), /Fair case/);
  assert.strictEqual(await page.locator('.meter span.on').count(), 2);
  await page.click('.chip >> nth=0');
  assert.ok((await page.textContent('#drawer')).includes('Platelet count 85,000'));
  await page.click('#close');
  await page.evaluate(() => { location.hash = 'letter'; });
  assert.ok((await page.textContent('main')).includes('₹42,000'));

  // Live checker: a real letter analysed in the browser with the rules engine.
  await page.evaluate(() => { location.hash = 'try'; });
  await page.click('#trysample');
  await page.click('#tryform button[type=submit]');
  assert.match(await page.textContent('main h2'), /Strong case/);
  assert.ok((await page.textContent('main')).includes('The moratorium protects this claim'));
  assert.ok((await page.textContent('main .doc mark >> nth=0')).includes('repudiated under Clause 6.2'));
  await page.click('#trydraft');
  assert.ok((await page.textContent('#trylet')).includes('Chapter I para 13'));
  await page.fill('#trytext', 'Your claim for Rs. 40,000 is rejected as the hospitalisation was not medically necessary.');
  await page.fill('#trystart', '');
  await page.click('#tryform button[type=submit]');
  assert.ok((await page.textContent('main')).includes('does not cite the policy terms'));
  await audit(page, 'checker/results', failures);

  // PDF upload: a PDF made in the browser is read with pdf.js (CDN served from the npm copy) and analysed.
  const pdfDir = path.dirname(require.resolve('pdfjs-dist/build/pdf.min.js'));
  await page.route('https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/*', r =>
    r.fulfill({ path: path.join(pdfDir, path.basename(new URL(r.request().url()).pathname)), contentType: 'application/javascript' }));
  const maker = await browser.newPage();
  await maker.setContent('<p>Dear Sir,</p><p>Your claim for Rs. 62,000 is rejected as the documents requested have not been submitted. Hence the claim is closed under Clause 9.1.</p>');
  const pdf = await maker.pdf();
  await maker.close();
  await page.setInputFiles('#trypdf', { name: 'rejection.pdf', mimeType: 'application/pdf', buffer: pdf });
  await page.waitForFunction(() => document.getElementById('trytext').value.includes('Clause 9.1'), null, { timeout: 15000 });
  assert.ok((await page.textContent('#trypdfmsg')).startsWith('Read rejection.pdf'));
  await page.click('#tryform button[type=submit]');
  assert.ok((await page.textContent('main')).includes('The insurer must collect the documents itself'));

  await browser.close();
  if (failures.length) {
    console.error('Accessibility violations (serious/critical):\n' + failures.join('\n'));
    process.exit(1);
  }
  console.log('Prototype e2e + accessibility: all checks passed');
})().catch(e => { console.error(e); process.exit(1); });
