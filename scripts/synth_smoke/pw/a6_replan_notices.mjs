// A6 재계획 보존(D9)·외부(Garmin) 안내 스모크. 보존/외부 행이 심긴 DB 필요. 환경: BASE
import { chromium } from 'playwright';
const b = await chromium.launch(); const page = await (await b.newContext({ viewport: { width: 390, height: 844 } })).newPage();
const errs = []; page.on('response', (r) => { if (r.status() >= 400) errs.push(r.status() + ' ' + r.url()); });
const B = (process.env.BASE || 'http://127.0.0.1:18111') + '/v2';
await page.goto(B + '/coach/plan/replan', { waitUntil: 'networkidle' }); await page.waitForTimeout(1200);
console.log(await page.locator('main').innerText());
await page.screenshot({ path: 'shots/replan_5_notices.png', fullPage: true });
await page.getByRole('button', { name: /적용/ }).click(); await page.waitForTimeout(1500);
await page.getByRole('link', { name: '계획 보기' }).click(); await page.waitForTimeout(1500);
console.log('url after 계획 보기:', page.url());
await page.goBack(); await page.waitForTimeout(1000);
console.log('url after back:', page.url(), '| errors:', errs);
await b.close();
