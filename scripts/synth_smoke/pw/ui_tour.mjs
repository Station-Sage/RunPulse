// 실 계정 사본 UI 순회: 주요 화면을 모바일(390)·데스크톱(1280)으로 캡처하고 텍스트·콘솔 에러 수집
import { chromium } from 'playwright';
const BASE = process.env.BASE || 'http://127.0.0.1:18110';
const routes = (process.env.ROUTES || '/v2/today').split(',');
const b = await chromium.launch();
const errs = [];
for (const [w, h, tag] of [[390, 844, 'm'], [1280, 900, 'd']]) {
  const ctx = await b.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  page.on('console', (m) => { if (m.type() === 'error') errs.push(`[${tag}][console] ${m.text().slice(0, 160)}`); });
  page.on('pageerror', (e) => errs.push(`[${tag}][pageerror] ${e.message.slice(0, 160)}`));
  page.on('response', (r) => { if (r.status() >= 400) errs.push(`[${tag}][http ${r.status()}] ${r.url().replace(BASE, '')}`); });
  for (const r of routes) {
    await page.goto(BASE + r, { waitUntil: 'networkidle' });
    await page.waitForTimeout(900);
    const name = r.replace(/[^a-z0-9]+/gi, '_').replace(/^_|_$/g, '');
    await page.screenshot({ path: `shots/ui_${name}_${tag}.png`, fullPage: true });
    const info = await page.evaluate(() => ({ h: document.documentElement.scrollHeight, w: document.documentElement.scrollWidth, vw: innerWidth }));
    console.log(tag, r, `h=${info.h}`, info.w > info.vw ? '⚠ overflow' : 'ok');
  }
  await ctx.close();
}
console.log('ERRORS', errs.length); errs.forEach((e) => console.log(' ', e));
await b.close();
