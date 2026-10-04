// 활동 목록 기간 필터·URL 동기화. 환경: BASE, API
import { chromium } from 'playwright';
const BASE = process.env.BASE || 'http://127.0.0.1:5199';
const API = process.env.API || 'http://127.0.0.1:18098';
const b = await chromium.launch();
const ctx = await b.newContext({ viewport: { width: 390, height: 900 } });
const seen = [];
await ctx.route('**/api/v1/**', (r) => {
	const u = r.request().url();
	if (u.includes('/library/activities?')) seen.push(new URL(u).search);
	r.continue({ url: u.replace(/^https?:\/\/[^/]+/, API) });
});
const page = await ctx.newPage();
const errs = [];
page.on('pageerror', (e) => errs.push(e.message));
await page.goto(`${BASE}/v2/library/activities`, { waitUntil: 'networkidle' });
const count = async () => (await page.locator('ul.divide-y > li').count());
console.log('all:', await count(), page.url().split('/v2')[1]);
await page.getByRole('button', { name: '최근 30일' }).click();
await page.waitForLoadState('networkidle');
console.log('30d:', await count(), page.url().split('/v2')[1]);
await page.getByRole('button', { name: '러닝' }).click();
await page.waitForLoadState('networkidle');
console.log('30d+running:', await count(), page.url().split('/v2')[1]);
await page.reload({ waitUntil: 'networkidle' });
console.log('reload keeps:', await count(), page.url().split('/v2')[1],
	'pressed:', await page.getByRole('button', { name: '최근 30일' }).getAttribute('aria-pressed'));
await page.getByLabel('월 선택').selectOption({ index: 2 });
await page.waitForLoadState('networkidle');
console.log('month:', await count(), page.url().split('/v2')[1]);
await page.getByRole('button', { name: '전체' }).first().click();
await page.waitForLoadState('networkidle');
console.log('reset url:', page.url().split('/v2')[1]);
await page.screenshot({ path: 'shots/activities_filter.png', fullPage: false });
console.log('requests:', seen.slice(-3), 'errors:', errs);
await b.close();
