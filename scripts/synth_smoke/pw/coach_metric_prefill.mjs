// 지표 → Coach 프리필 + 탐색 프리페치 스모크. 환경: FE(vite), API(합성 서버)
import { chromium } from 'playwright';
const FE = process.env.FE || 'http://127.0.0.1:5199', API = process.env.API || 'http://127.0.0.1:18771';
const b = await chromium.launch();
const page = await (await b.newContext({ viewport: { width: 390, height: 844 } })).newPage();
const explain = [];
await page.route('**/api/v1/**', async (r) => {
	const u = new URL(r.request().url());
	if (u.pathname.includes('/explain')) explain.push(u.pathname + u.search);
	const res = await r.fetch({ url: API + u.pathname + u.search });
	await r.fulfill({ response: res });
});
const errs = []; page.on('pageerror', (e) => errs.push(e.message));
await page.goto(FE + '/v2/coach/new?metric=tsb&date=2026-09-20', { waitUntil: 'networkidle' });
console.log('metric-card:', await page.getByTestId('metric-card').innerText().catch(() => 'MISSING'));
console.log('questions:', (await page.getByTestId('suggested-question').allInnerTexts()).length);
await page.goto(FE + '/v2/coach/new?metric=bad%20slug&date=x', { waitUntil: 'networkidle' });
console.log('invalid → card:', await page.getByTestId('metric-card').count());
console.log('explain requests', explain.length, 'errors', errs.length);
await b.close();
