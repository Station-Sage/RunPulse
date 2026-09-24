// 데스크톱 폭(1280) 스크린샷 — shots/wide_*.png. 환경: BASE, ROUTES
import { chromium } from 'playwright';
const BASE = process.env.BASE || 'http://127.0.0.1:18099';
const b = await chromium.launch();
const page = await (await b.newContext({ viewport: { width: 1280, height: 800 } })).newPage();
for (const r of (process.env.ROUTES || '/v2/today').split(',')) {
  await page.goto(BASE + r, { waitUntil: 'networkidle' });
  const f = 'wide_' + r.replace(/[^a-z0-9]+/gi, '_') + '.png';
  await page.screenshot({ path: new URL('./shots/' + f, import.meta.url).pathname });
  console.log(f);
}
await b.close();
