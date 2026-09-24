// 라우트별 스크린샷(pw/shots/) + ACTIONS(JSON)로 클릭 시나리오 후 다이얼로그 텍스트 출력. 환경: BASE, ROUTES, ACTIONS
import { chromium } from 'playwright';
const BASE = process.env.BASE || 'http://127.0.0.1:18099';
const OUT = new URL('./shots/', import.meta.url).pathname;
const routes = (process.env.ROUTES || '/v2/today,/v2/library,/v2/library/activities,/v2/library/100,/v2/library/100/streams,/v2/library/100/providers,/v2/library/providers,/v2/library/metrics,/v2/coach,/v2/coach/1,/v2/coach/plan').split(',');
const b = await chromium.launch();
const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
const errs = [];
const page = await ctx.newPage();
page.on('console', (m) => { if (m.type() === 'error') errs.push(`[console] ${page.url()} :: ${m.text()}`); });
page.on('pageerror', (e) => errs.push(`[pageerror] ${page.url()} :: ${e.message}`));
page.on('requestfailed', (r) => errs.push(`[reqfailed] ${r.url()} ${r.failure()?.errorText}`));
page.on('response', (r) => { if (r.status() >= 400) errs.push(`[http ${r.status()}] ${r.url()}`); });
const slug = (s) => s.replace(/[^a-z0-9]+/gi, '_').replace(/^_|_$/g, '');
for (const r of routes) {
  await page.goto(BASE + r, { waitUntil: 'networkidle' });
  await page.waitForTimeout(400);
  await page.screenshot({ path: OUT + slug(r) + '.png', fullPage: true });
  console.log('shot', r, '→', slug(r) + '.png', '| title:', await page.title());
}
// 인터랙션 스크립트(옵션): ACTIONS=json
if (process.env.ACTIONS) {
  for (const a of JSON.parse(process.env.ACTIONS)) {
    try {
    await page.goto(BASE + a.route, { waitUntil: 'networkidle' });
    for (const step of a.steps) {
      if (step.click) await page.getByText(step.click, { exact: step.exact ?? false }).first().click();
      if (step.clickSel) await page.locator(step.clickSel).first().click();
      if (step.fill) await page.locator(step.fill[0]).first().fill(step.fill[1]);
      await page.waitForTimeout(step.wait ?? 500);
    }
    const dlg = await page.locator('[role=dialog]').last().innerText().catch(() => null);
    console.log('dialog[' + a.name + ']:', dlg ? dlg.replace(/\n+/g, ' | ').slice(0, 600) : '(no dialog)');
    await page.screenshot({ path: OUT + a.name + '.png', fullPage: false });
    console.log('action shot', a.name);
    } catch (e) { console.log('ACTION FAILED', a.name, String(e.message).split('\n')[0]); }
  }
}
console.log('ERRORS:', errs.length); for (const e of errs) console.log(e);
await b.close();
