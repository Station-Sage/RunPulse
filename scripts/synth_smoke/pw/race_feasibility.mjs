// 레이스 허브 목표 달성 가능성(필요 개선 %) 실 데이터 사본 스모크. 환경: BASE, API
import { chromium } from 'playwright';
const BASE = process.env.BASE || 'http://127.0.0.1:5199';
const API = process.env.API || 'http://127.0.0.1:18098';
const b = await chromium.launch();
const ctx = await b.newContext({ viewport: { width: 1280, height: 1000 } });
await ctx.route('**/api/v1/**', (r) => r.continue({ url: r.request().url().replace(/^https?:\/\/[^/]+/, API) }));
const page = await ctx.newPage();
const errs = [];
page.on('pageerror', (e) => errs.push(e.message));
await page.goto(`${BASE}/v2/today/race`, { waitUntil: 'networkidle' });
const sum = page.locator('section[aria-label="레이스 예측 요약"]');
console.log('summary:', await sum.count() ? (await sum.innerText()).replace(/\s+/g, ' ').slice(0, 300) : 'none');
console.log('required-improvement:', await page.locator('[data-testid=required-improvement]').count());
await page.screenshot({ path: 'shots/race_feasibility.png', fullPage: true });
console.log('errors:', errs);
await b.close();
