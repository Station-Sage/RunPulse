// 활동 → 코치에게 묻기 플로우. 환경: FE(vite), API(합성 서버)
import { chromium } from 'playwright';
const FE = process.env.FE || 'http://127.0.0.1:5199', API = process.env.API || 'http://127.0.0.1:18771';
const b = await chromium.launch();
const page = await (await b.newContext({ viewport: { width: 390, height: 844 } })).newPage();
await page.route('**/api/v1/**', async (r) => {
	const u = new URL(r.request().url());
	const res = await r.fetch({ url: API + u.pathname + u.search });
	await r.fulfill({ response: res });
});
const errs = []; page.on('response', (r) => { if (r.status() >= 400) errs.push(r.status() + ' ' + r.url()); });
await page.goto(FE + '/v2/library/100', { waitUntil: 'networkidle' });
console.log('cta visible:', await page.getByTestId('ask-coach-cta').isVisible(), 'inline hidden:', !(await page.getByTestId('ask-coach').isVisible()));
await page.screenshot({ path: '/tmp/ask1.png' });
await page.getByTestId('ask-coach-cta').click();
await page.waitForURL(/coach\/new\?activity=100/);
await page.waitForSelector('[data-testid=evidence-card]');
console.log('chips:', await page.getByTestId('evidence-chip').allInnerTexts());
console.log('questions:', await page.getByTestId('suggested-question').allInnerTexts());
await page.screenshot({ path: '/tmp/ask2.png' });
await page.getByTestId('suggested-question').first().click();
await page.waitForTimeout(1500);
console.log('url after:', page.url(), '| scope sheet:', await page.locator('text=동의').count());
await page.screenshot({ path: '/tmp/ask3.png' });
console.log('back href:', await page.getByTestId('thread-back').getAttribute('href'));
console.log('errors:', errs);
await b.close();
