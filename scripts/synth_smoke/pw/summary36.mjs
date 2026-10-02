import { chromium } from 'playwright';
const BASE = process.env.BASE || 'http://127.0.0.1:18099';
const b = await chromium.launch();
for (const [name, vp] of [['desk', { width: 1200, height: 900 }], ['mob', { width: 390, height: 844 }]]) {
  const page = await (await b.newContext({ viewport: vp })).newPage();
  const errs = []; page.on('pageerror', (e) => errs.push(e.message)); page.on('console', (m) => m.type() === 'error' && errs.push(m.text()));
  await page.goto(BASE + '/v2/library/100', { waitUntil: 'networkidle' });
  await page.waitForTimeout(500);
  const t = (id) => page.locator(`[data-testid=${id}]`).count();
  console.log(name, 'map', await t('route-map'), 'splits', await t('split-row'), 'zones', await t('hr-zones'), 'env', await t('env-line'), 'coach', await t('ask-coach'), 'sw', await page.evaluate(() => [document.documentElement.scrollWidth, innerWidth]));
  const rows = page.locator('[data-testid=split-row]');
  if (await rows.count()) {
    await rows.nth(2).click();
    console.log(' pressed', await rows.nth(2).getAttribute('aria-pressed'));
    await page.screenshot({ path: `/tmp/s36-${name}-sel.png`, fullPage: true });
    await rows.nth(2).click();
    console.log(' toggled off', await rows.nth(2).getAttribute('aria-pressed'));
  }
  const tl = page.locator('[role=group][aria-label*=스크럽]').first();
  if (await tl.count()) { const bx = await tl.boundingBox(); await page.mouse.move(bx.x + bx.width * 0.5, bx.y + 30); await page.waitForTimeout(200); console.log(' cursor', await t('route-cursor')); }
  await page.screenshot({ path: `/tmp/s36-${name}.png`, fullPage: true });
  console.log(' errs', errs.slice(0, 3));
}
await b.close();
