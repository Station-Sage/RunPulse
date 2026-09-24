// 플랜 생성 폼 → 생성 → 세션 상세까지의 흐름. 환경: BASE
import { chromium } from 'playwright';
const b = await chromium.launch(); const page = await (await b.newContext({ viewport: { width: 390, height: 844 } })).newPage();
const errs = []; page.on('response', async (r) => { if (r.status() >= 400) errs.push(r.status() + ' ' + r.request().method() + ' ' + r.url()); });
page.on('pageerror', (e) => errs.push('pageerror ' + e.message));
const B = (process.env.BASE || 'http://127.0.0.1:18099') + '/v2';
const txt = async () => (await page.locator('body').innerText()).replace(/\n+/g, ' | ').slice(0, 700);
await page.goto(B + '/coach/plan/new', { waitUntil: 'networkidle' });
console.log('new:', await txt());
await page.getByText('하프', { exact: true }).click();
await page.waitForTimeout(300);
const date = page.locator('input[type=date]').first();
if (await date.count()) await date.fill('2026-12-20');
await page.getByText('프로그램 생성').click();
await page.waitForTimeout(1500);
console.log('url after create:', page.url());
console.log('after:', await txt());
// session detail
await page.goto(B + '/coach/plan/1/session/2026-09-24', { waitUntil: 'networkidle' });
console.log('session:', await txt());
console.log('errors:', errs);
await b.close();
