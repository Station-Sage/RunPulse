// 신규 계정 T12: 빈 DB(200) Today → /welcome 리다이렉트 후 단계별 탭 수. sync-state는 소스 0으로 모킹. 환경: BASE
import { chromium } from 'playwright';
const b = await chromium.launch(); const page = await (await b.newContext({ viewport: { width: 390, height: 844 } })).newPage();
const errs = []; page.on('pageerror', (e) => errs.push(e.message));
await page.route('**/api/v1/data/sync-state', async (r) => {
	const res = await r.fetch(); const j = await res.json();
	j.data.connected_count = 0; j.data.activity_count = 0; await r.fulfill({ response: res, json: j });
});
const B = (process.env.BASE || 'http://127.0.0.1:18998') + '/v2';
await page.goto(B + '/today', { waitUntil: 'networkidle' });
await page.waitForTimeout(800);
console.log('after today:', page.url().replace(B, ''));
let taps = 0;
for (let i = 0; i < 10; i++) {
	const btns = (await page.locator('main button:visible, main a:visible').allInnerTexts()).map((t) => t.trim()).filter(Boolean);
	console.log('step', i, page.url().replace(B, ''), JSON.stringify(btns.slice(0, 8)));
	const next = page.locator('main button:visible', { hasText: /다음|건너뛰|시작|나중에|계속/ }).first();
	if (!(await next.count())) break;
	await next.click(); taps++; await page.waitForTimeout(500);
}
console.log('taps', taps, 'final', page.url().replace(B, ''), 'errors', errs);
await b.close();
