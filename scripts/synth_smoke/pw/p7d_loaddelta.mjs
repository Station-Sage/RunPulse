// Phase 7d: 행 액션 시트의 부하 미리보기 한 줄 390px 스모크. 환경: BASE
import { chromium } from 'playwright';
const b = await chromium.launch(); const page = await (await b.newContext({ viewport: { width: 390, height: 844 } })).newPage();
const errs = []; page.on('response', (r) => { if (r.status() >= 400) errs.push(r.status() + ' ' + r.request().method() + ' ' + r.url()); });
page.on('pageerror', (e) => errs.push('pageerror ' + e.message));
const B = (process.env.BASE || 'http://127.0.0.1:18097') + '/v2';
await page.goto(B + '/coach/plan/1', { waitUntil: 'networkidle' });
await page.getByTestId('row-action-btn').first().click();
await page.getByTestId('row-op-rest').click(); await page.waitForTimeout(1000);
const el = page.getByTestId('load-delta');
console.log('load-delta visible:', await el.count(), (await el.count()) ? await el.first().innerText() : '');
await page.screenshot({ path: 'shots/p7d_loaddelta.png' });
console.log('errors:', errs);
await b.close();
