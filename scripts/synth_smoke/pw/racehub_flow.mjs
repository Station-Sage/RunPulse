// 레이스 허브(P7-PRED-72/73/74) 실동작: 상세 펼치기 → 3-way 비교·근거·대회 확인 클릭 → API 반영·되돌리기
import { chromium } from 'playwright';
const BASE = process.env.BASE || 'http://127.0.0.1:18101';
const b = await chromium.launch();
const errs = [];
for (const [w, h] of [[390, 844], [1280, 900]]) {
  const ctx = await b.newContext({ viewport: { width: w, height: h } });
  const page = await ctx.newPage();
  page.on('console', (m) => { if (m.type() === 'error') errs.push(`[${w}][console] ${m.text()}`); });
  page.on('pageerror', (e) => errs.push(`[${w}][pageerror] ${e.message}`));
  page.on('response', (r) => { if (r.status() >= 400) errs.push(`[${w}][http ${r.status()}] ${r.url()}`); });
  await page.goto(BASE + '/v2/today', { waitUntil: 'networkidle' });
  const sc = await page.evaluate(() => [document.documentElement.scrollWidth, innerWidth]);
  console.log(`\n== ${w}px scrollW/vw`, sc.join('/'), sc[0] > sc[1] ? '⚠ OVERFLOW' : 'ok');
  const summary = page.locator('summary', { hasText: '예측 추이' });
  console.log('summary 존재', await summary.count());
  await summary.first().click();
  await page.waitForTimeout(1200);
  const txt = await page.locator('details').first().innerText();
  console.log('상세 텍스트(앞 900자):', txt.replace(/\n+/g, ' | ').slice(0, 900));
  await page.screenshot({ path: `shots/racehub_${w}.png`, fullPage: true });
  if (w === 390) {
    const row = page.locator('li', { hasText: 'Forest run' }).first();
    console.log('Forest run 행 있음', await row.count());
    const paced = row.getByRole('button', { name: '페이스' });
    await paced.click(); await page.waitForTimeout(700);
    let api = await (await page.request.get(BASE + '/api/v1/races/candidates')).json();
    let it = (api.data ?? api).items.find((i) => i.name === 'Forest run');
    console.log('페이스 클릭 후 API confirmed_effort =', it.confirmed_effort);
    await paced.click(); await page.waitForTimeout(700);
    api = await (await page.request.get(BASE + '/api/v1/races/candidates')).json();
    it = (api.data ?? api).items.find((i) => i.name === 'Forest run');
    console.log('다시 클릭(되돌리기) 후 API confirmed_effort =', it.confirmed_effort);
  }
  await ctx.close();
}
console.log('\nERRORS:', errs.length); errs.forEach((e) => console.log(' ', e));
await b.close();
