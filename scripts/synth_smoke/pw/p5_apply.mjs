// 훈련 방식 변경 적용·되돌리기 스모크. 환경: BASE
import { chromium } from 'playwright';
const b = await chromium.launch(); const page = await (await b.newContext({ viewport: { width: 375, height: 800 } })).newPage();
const errs = []; page.on('response', (r) => { if (r.status() >= 400) errs.push(r.status() + ' ' + r.url()); });
const B = (process.env.BASE || 'http://127.0.0.1:18355') + '/v2';
await page.goto(B + '/coach/plan/replan', { waitUntil: 'networkidle' }); await page.waitForTimeout(1200);
await page.locator('details summary').first().click();
await page.getByTestId('method-card-threshold_tempo').getByRole('button').click();
await page.getByRole('button', { name: '다시 계산' }).click(); await page.waitForTimeout(1500);
await page.getByRole('button', { name: /적용/ }).click(); await page.waitForTimeout(1800);
console.log('applied:', (await page.locator('main').innerText()).slice(0, 200).replace(/\n/g, ' | '));
await page.getByRole('button', { name: '되돌리기' }).click(); await page.waitForTimeout(1500);
console.log('undone:', (await page.locator('main').innerText()).slice(0, 200).replace(/\n/g, ' | '));
await page.getByRole('button', { name: '되돌리기 진행' }).click(); await page.waitForTimeout(1500);
console.log('errors:', errs); await b.close();
