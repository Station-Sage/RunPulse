// 예측 분해(PredictionEvidence) 실 데이터 사본 스모크. 환경: BASE, API, DATE
import { chromium } from 'playwright';
const BASE = process.env.BASE || 'http://127.0.0.1:5199';
const API = process.env.API || 'http://127.0.0.1:18098';
const date = process.env.DATE || '2026-10-04';
const b = await chromium.launch();
for (const slug of ['race_pred_marathon_sec', 'race_pred_10k_sec']) {
	const ctx = await b.newContext({ viewport: { width: 1280, height: 1000 } });
	await ctx.route('**/api/v1/**', (r) => r.continue({ url: r.request().url().replace(/^https?:\/\/[^/]+/, API) }));
	const page = await ctx.newPage();
	const errs = [];
	page.on('pageerror', (e) => errs.push(e.message));
	await page.goto(`${BASE}/v2/library/metrics/${slug}?period=3m&date=${date}`, { waitUntil: 'networkidle' });
	const ev = page.locator('[data-testid=prediction-evidence]');
	console.log(slug, 'evidence visible:', await ev.count(), (await ev.count()) ? (await ev.innerText()).replace(/\s+/g, ' ').slice(0, 300) : '');
	await page.screenshot({ path: `shots/pred_${slug}.png`, fullPage: true });
	console.log('errors:', errs);
	await ctx.close();
}
await b.close();
