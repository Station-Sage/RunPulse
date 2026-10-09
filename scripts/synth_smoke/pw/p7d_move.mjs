// Phase 7d: 행 액션 move(날짜 칩·거절·되돌리기) 390px 스모크. 환경: BASE
import { chromium } from 'playwright';
const b = await chromium.launch(); const page = await (await b.newContext({ viewport: { width: 390, height: 844 } })).newPage();
const errs = []; page.on('response', (r) => { if (r.status() >= 400) errs.push(r.status() + ' ' + r.request().method() + ' ' + r.url()); });
page.on('pageerror', (e) => errs.push('pageerror ' + e.message));
const B = (process.env.BASE || 'http://127.0.0.1:18111') + '/v2';
const txt = async () => (await page.locator('body').innerText()).replace(/\n+/g, ' | ');
const today = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
await page.goto(B + '/coach/plan/1', { waitUntil: 'networkidle' });
const idx = await page.evaluate((t) => [...document.querySelectorAll('[data-testid=row-action-btn]')].length, today);
const rows = page.locator('li:has([data-testid=row-action-btn])');
const todayRow = rows.first();
await todayRow.getByTestId('row-action-btn').click();
await page.getByTestId('row-op-move').click();
const chips = await page.locator('[data-testid^=move-day-]').count();
console.log('buttons:', idx, 'chips:', chips, 'apply disabled:', await page.getByTestId('row-action-apply').isDisabled());
await page.screenshot({ path: 'shots/p7d_move_sheet.png' });
// 강한 훈련(롱런) 날 → 거절
await page.locator('[data-testid^=move-day-]').first().click();
await page.getByTestId('row-action-apply').click(); await page.waitForTimeout(1200);
console.log('reject1:', (await txt()).match(/강한 훈련[^|]*|옮겼어요/)?.[0]);
// 휴식 날 선택
const chipsNow = page.locator('[data-testid^=move-day-]');
if (await chipsNow.count()) { await chipsNow.nth(1).click(); await page.getByTestId('row-action-apply').click(); await page.waitForTimeout(1500); }
console.log('moved:', /옮겼어요/.test(await txt()));
await page.screenshot({ path: 'shots/p7d_move_after.png', fullPage: true });
await page.getByRole('button', { name: '되돌리기' }).first().click(); await page.waitForTimeout(1200);
console.log('undone:', /원래 계획으로/.test(await txt()));
console.log('errors:', errs);
await b.close();
