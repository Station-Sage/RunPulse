// 라우트별 innerText·가로 넘침(390px)·콘솔/HTTP 에러 점검. 환경: BASE, ROUTES(콤마 구분), TXT(출력 글자 수)
import { chromium } from 'playwright';
const BASE = process.env.BASE || 'http://127.0.0.1:18099';
const routes = (process.env.ROUTES || '/v2/today').split(',');
const b = await chromium.launch();
const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
const page = await ctx.newPage();
const errs = [];
page.on('console', (m) => { if (m.type() === 'error') errs.push(`[console] ${m.text()}`); });
page.on('pageerror', (e) => errs.push(`[pageerror] ${e.message}`));
page.on('response', (r) => { if (r.status() >= 400) errs.push(`[http ${r.status()}] ${r.url()}`); });
for (const r of routes) {
  await page.goto(BASE + r, { waitUntil: 'networkidle' });
  await page.waitForTimeout(300);
  const TXT = Number(process.env.TXT || 500);
  const info = await page.evaluate((TXT) => {
    const vw = window.innerWidth;
    const over = [];
    document.querySelectorAll('body *').forEach((el) => {
      const rc = el.getBoundingClientRect();
      if (rc.width > 0 && (rc.right > vw + 1 || rc.left < -1)) over.push(el.tagName + '.' + (el.className?.toString().slice(0, 40) || '') + ` [${Math.round(rc.left)}..${Math.round(rc.right)}]`);
    });
    return { scrollW: document.documentElement.scrollWidth, vw, overflow: over.slice(0, 5), text: document.body.innerText.replace(/\n+/g, ' | ').slice(0, TXT) };
  }, TXT);
  console.log('\n==', r, '\n scrollW', info.scrollW, 'vw', info.vw, info.scrollW > info.vw ? '⚠ HORIZONTAL OVERFLOW' : 'ok');
  if (info.overflow.length) console.log(' overflowing:', info.overflow);
  console.log(' text:', info.text);
}
console.log('\nERRORS:', errs.length); errs.forEach((e) => console.log(' ', e));
await b.close();
