// Browser tests for the prototype, plus an axe-core accessibility audit (WCAG 2.2 AA).
// Run:  npm i playwright@1.63.0 axe-core@4.10.2 && npx playwright install chromium && node tests/e2e/prototype.e2e.cjs
const { chromium } = require('playwright');
const path = require('path');
const assert = require('assert');

const AXE = require.resolve('axe-core/axe.min.js');
const PAGE = 'file://' + path.resolve(__dirname, '../../prototype/index.html');
const SCREENS = ['home', 'upload', 'analyse', 'verdict', 'letter', 'track'];

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

  await browser.close();
  if (failures.length) {
    console.error('Accessibility violations (serious/critical):\n' + failures.join('\n'));
    process.exit(1);
  }
  console.log('Prototype e2e + accessibility: all checks passed');
})().catch(e => { console.error(e); process.exit(1); });
