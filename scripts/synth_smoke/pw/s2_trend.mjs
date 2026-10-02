// 메트릭 상세 차트 S2 검증 — 밴드·기준선·aria-label·기간 전환. 환경: BASE(vite), API(합성 서버), SLUG
import { chromium } from 'playwright';
const BASE = process.env.BASE || 'http://127.0.0.1:5199';
const API = process.env.API || 'http://127.0.0.1:18098';
const b = await chromium.launch();
const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
await ctx.route('**/api/v1/**', (r) => r.continue({ url: r.request().url().replace(/^https?:\/\/[^/]+/, API) }));
const page = await ctx.newPage();
const errs = [];
page.on('pageerror', (e) => errs.push(e.message));
const slug = process.env.SLUG || 'utrs';
for (const period of ['4w', '3m']) {
	await page.goto(`${BASE}/v2/library/metrics/${slug}?period=${period}`, { waitUntil: 'networkidle' });
	const chart = page.locator('[role=slider][aria-label*="눌러서"]');
	console.log(period, 'aria:', await chart.getAttribute('aria-label'));
	console.log(period, 'bands:', await page.locator('svg rect[fill-opacity="0.08"]').count(), 'polylines:', await page.locator('svg polyline').count());
	await page.screenshot({ path: new URL(`./shots/s2_${slug}_${period}.png`, import.meta.url).pathname });
}
console.log('errors:', errs);
await b.close();
