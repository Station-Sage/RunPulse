// 새 플랜 생성 화면의 훈련 방식 선택 스모크 — 데스크톱+375px. 환경: BASE
import { chromium } from 'playwright';
const b = await chromium.launch();
const B = (process.env.BASE || 'http://127.0.0.1:18356') + '/v2';
for (const [name, w, h] of [['desk', 1280, 900], ['m375', 375, 800]]) {
  const page = await (await b.newContext({ viewport: { width: w, height: h } })).newPage();
  const errs = [];
  page.on('response', (r) => { if (r.status() >= 400) errs.push(r.status() + ' ' + r.url()); });
  page.on('pageerror', (e) => errs.push('pageerror ' + e.message));
  await page.goto(B + '/coach/plan/new', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: '마라톤' }).click();
  for (const d of ['월', '수', '금']) await page.getByRole('button', { name: d, exact: true }).click().catch(() => {});
  await page.waitForTimeout(1500);
  console.log(name, 'picker:', await page.getByTestId('new-plan-method').isVisible(), 'cards', await page.locator('[data-testid^="method-card-"]').count());
  await page.screenshot({ path: `shots/p6_new_${name}.png`, fullPage: true });
  console.log(name, 'errs', JSON.stringify(errs));
}
await b.close();
