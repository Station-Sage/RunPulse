// U17f 월간 라우트 스모크 — Today 진입, ‹ › 히스토리 불변, 칩 → DrillPanel 1개, 뒤로가기. 환경: BASE
import { chromium } from 'playwright';
const BASE = process.env.BASE || 'http://127.0.0.1:18098';
const b = await chromium.launch();
const page = await (await b.newContext({ viewport: { width: 390, height: 800 } })).newPage();
const errs = [];
page.on('pageerror', (e) => errs.push(e.message));
await page.goto(BASE + '/v2/today', { waitUntil: 'networkidle' });
await page.goto(BASE + '/v2/today/month/2026-10', { waitUntil: 'networkidle' });
console.log('title', await page.locator('[data-testid=month-title]').innerText());
const h0 = await page.evaluate(() => history.length);
await page.getByLabel('이전 달').click();
await page.waitForTimeout(500);
console.log('title', await page.locator('[data-testid=month-title]').innerText(), 'url', page.url());
console.log('history unchanged', h0 === (await page.evaluate(() => history.length)));
await page.getByLabel('다음 달').click();
await page.waitForTimeout(500);
console.log('modals', await page.locator('[aria-modal=true]').count());
const chip = page.locator('button').filter({ hasText: /CTL|km|TSB/ }).first();
if (await chip.count()) { await chip.click(); await page.waitForTimeout(600); }
console.log('modals after chip', await page.locator('[aria-modal=true]').count());
await page.goto(BASE + '/v2/today', { waitUntil: 'networkidle' });
await page.locator('button', { hasText: /월간|이번 달|한 달/ }).first().click().catch(() => console.log('no month btn'));
await page.waitForTimeout(500);
console.log('entry url', page.url());
console.log('errors', errs.length, errs.slice(0, 2));
await b.close();
