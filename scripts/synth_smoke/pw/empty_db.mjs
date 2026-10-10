// 빈 DB 신규 계정 스모크: Today 빈 상태→/welcome 진입, 단계별 탭 수(T12≤8), 콘솔 오류. 환경: BASE
import { chromium } from 'playwright';
const b = await chromium.launch(); const page = await (await b.newContext({ viewport: { width: 390, height: 844 } })).newPage();
const errs = []; page.on('pageerror', (e) => errs.push(e.message));
const B = (process.env.BASE || 'http://127.0.0.1:18998') + '/v2';
for (const p of ['/today', '/library', '/coach', '/library/metrics/cirs']) {
	await page.goto(B + p, { waitUntil: 'networkidle' });
	const txt = (await page.locator('main').innerText()).replace(/\s+/g, ' ').slice(0, 160);
	console.log(p, '->', page.url().replace(B, ''), '|', txt);
}
await page.goto(B + '/today', { waitUntil: 'networkidle' });
let taps = 0;
for (let i = 0; i < 10; i++) {
	const btns = await page.locator('main button:visible, main a:visible').allInnerTexts();
	console.log('step', i, page.url().replace(B, ''), JSON.stringify(btns.map((t) => t.trim()).filter(Boolean).slice(0, 8)));
	const next = page.locator('main button:visible', { hasText: /다음|건너뛰|시작|나중에|계속/ }).first();
	if (!(await next.count())) break;
	await next.click(); taps++; await page.waitForTimeout(400);
}
console.log('taps', taps, 'errors', errs);
await b.close();
