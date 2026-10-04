// U11 활동 목록 스모크 — 필터·월 헤더·스크러버·무한 스크롤. 환경: BASE
import { chromium } from 'playwright';
const BASE = process.env.BASE || 'http://127.0.0.1:8766';
const b = await chromium.launch();
const page = await (await b.newContext({ viewport: { width: 390, height: 800 } })).newPage();
const errs = [];
page.on('pageerror', (e) => errs.push(e.message));
page.on('console', (m) => m.type() === 'error' && errs.push(m.text()));
const url = BASE + '/v2/library/activities';
await page.goto(url, { waitUntil: 'networkidle' });
const cnt = () => page.locator('[data-testid=shown-count]').innerText();
console.log('initial', await cnt(), 'weeks', await page.locator('[data-testid=week-header]').count());
await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
await page.waitForTimeout(1500);
console.log('after scroll', await cnt());
await page.goto(url + '?sort=distance', { waitUntil: 'networkidle' });
console.log('sort=distance weeks', await page.locator('[data-testid=week-header]').count());
await page.goto(url + '?month=2026-08', { waitUntil: 'networkidle' });
console.log('month hdr', (await page.locator('[data-testid=month-header]').innerText()).replace(/\s+/g, ' '));
await page.goto(url, { waitUntil: 'networkidle' });
const sc = page.locator('[data-testid=scrubber]');
console.log('scrubber', await sc.count());
if (await sc.count()) {
  const bb = await sc.boundingBox();
  await page.mouse.move(bb.x + bb.width / 2, bb.y + bb.height * 0.6);
  await page.mouse.down();
  await page.mouse.up();
  await page.waitForTimeout(1500);
  console.log('after jump', await cnt(), page.url());
}
await page.screenshot({ path: new URL('./shots/u11.png', import.meta.url).pathname });
console.log('errors', errs);
await b.close();
