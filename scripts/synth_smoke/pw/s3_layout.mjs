// 메트릭 상세 S3 — 데스크톱 8/4 열 배치와 "이 지표는" 모바일 접힘. 환경: BASE, API, SLUG
import { chromium } from 'playwright';
const BASE = process.env.BASE || 'http://127.0.0.1:5199';
const API = process.env.API || 'http://127.0.0.1:18098';
const slug = process.env.SLUG || 'tsb';
const b = await chromium.launch();
for (const [name, w] of [['desktop', 1280], ['mobile', 390]]) {
	const ctx = await b.newContext({ viewport: { width: w, height: 900 } });
	await ctx.route('**/api/v1/**', (r) => r.continue({ url: r.request().url().replace(/^https?:\/\/[^/]+/, API) }));
	const page = await ctx.newPage();
	const errs = [];
	page.on('pageerror', (e) => errs.push(e.message));
	await page.goto(`${BASE}/v2/library/metrics/${slug}?period=4w&date=2026-09-19`, { waitUntil: 'networkidle' });
	const about = page.locator('[data-testid=metric-about]');
	const panel = page.locator('[data-testid=breakdown-panel]');
	const ab = await about.boundingBox();
	const pb = await panel.boundingBox();
	const body = about.locator('div').first();
	console.log(name, 'about:', ab && [Math.round(ab.x), Math.round(ab.y)], 'panel:', pb && [Math.round(pb.x), Math.round(pb.y)], 'bodyVisible:', await body.isVisible());
	if (name === 'mobile') {
		await about.locator('button').click();
		console.log('mobile after click bodyVisible:', await body.isVisible());
	}
	await page.screenshot({ path: `shots/s3_layout_${name}.png`, fullPage: true });
	console.log(name, 'errors:', errs);
	await ctx.close();
}
await b.close();
