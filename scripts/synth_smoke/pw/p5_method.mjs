// 훈련 방식 선택(재계획 페이지) 스모크 — 데스크톱+375px. 환경: BASE
import { chromium } from 'playwright';
const b = await chromium.launch();
const B = (process.env.BASE || 'http://127.0.0.1:18355') + '/v2';
for (const [name, w, h] of [['desk', 1280, 900], ['m375', 375, 800]]) {
  const page = await (await b.newContext({ viewport: { width: w, height: h } })).newPage();
  const errs = []; const urls = [];
  page.on('response', (r) => { if (r.status() >= 400) errs.push(r.status() + ' ' + r.url()); if (r.url().includes('replan')) urls.push(r.url()); });
  page.on('pageerror', (e) => errs.push('pageerror ' + e.message));
  await page.goto(B + '/coach/plan/replan', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  const picker = page.getByTestId('method-picker');
  console.log(name, 'picker visible:', await picker.isVisible());
  console.log(name, 'cards:', await page.locator('[data-testid^="method-card-"]').count());
  await page.screenshot({ path: `shots/p5_method_${name}_1.png`, fullPage: true });
  await page.locator('details summary').first().click().catch(() => {});
  const cards = page.locator('[data-testid^="method-card-"]');
  const n = await cards.count();
  let picked = null;
  for (let i = 0; i < n; i++) {
    const c = cards.nth(i);
    if ((await c.innerText()).includes('현재')) continue;
    const btn = c.getByRole('button').first();
    if (await btn.isVisible()) { picked = await c.getAttribute('data-testid'); await btn.click(); break; }
  }
  console.log(name, 'picked:', picked);
  urls.length = 0;
  await page.getByRole('button', { name: '다시 계산' }).click(); await page.waitForTimeout(1500);
  console.log(name, 'preview urls with plan_method:', urls.filter((u) => u.includes('plan_method')).length);
  await page.screenshot({ path: `shots/p5_method_${name}_2.png`, fullPage: true });
  console.log(name, 'overflow:', await page.evaluate(() => document.documentElement.scrollWidth > innerWidth));
  console.log(name, 'errors:', errs);
}
await b.close();
