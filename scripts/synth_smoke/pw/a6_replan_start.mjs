// A6 재계획 시작점 카드 스모크 (390px). 환경: BASE
import { chromium } from 'playwright';
const b = await chromium.launch(); const page = await (await b.newContext({ viewport: { width: 390, height: 844 } })).newPage();
const errs = []; page.on('response', (r) => { if (r.status() >= 400) errs.push(r.status() + ' ' + r.url()); });
await page.goto((process.env.BASE || 'http://127.0.0.1:18111') + '/v2/coach/plan/replan', { waitUntil: 'networkidle' }); await page.waitForTimeout(1200);
console.log(await page.locator('main').innerText());
console.log('weekly input count:', await page.getByText('최근 주간 거리').count());
await page.getByRole('button', { name: '바꾸기' }).click();
await page.getByPlaceholder(/\d:\d/).first().fill('3:50:00'); await page.waitForTimeout(300);
await page.getByRole('button', { name: '다시 계산' }).click(); await page.waitForTimeout(1500);
console.log((await page.locator('main').innerText()).split('\n').slice(0, 8).join(' | '));
await page.screenshot({ path: 'shots/replan_6_start.png', fullPage: true });
console.log('errors:', errs); await b.close();
