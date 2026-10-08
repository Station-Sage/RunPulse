import { chromium } from 'playwright';
const BASE = process.env.BASE || 'http://127.0.0.1:18099';
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }).catch(() => chromium.launch());
let bad = 0;
for (const w of [1280, 390]) {
	const p = await (await b.newContext({ viewport: { width: w, height: 900 } })).newPage();
	const errs = [];
	p.on('console', (m) => m.type() === 'error' && errs.push(m.text()));
	p.on('response', (r) => r.status() >= 400 && errs.push(r.status() + ' ' + r.url()));
	await p.goto(`${BASE}/v2/coach/plan/compare?distance_km=42.195&target_time_sec=11940`);
	await p.waitForSelector('[data-testid=scenario-compare]');
	const n = await p.locator('[data-testid=scenario-compare] section').count();
	const badge = await p.getByText('권장', { exact: true }).count();
	const ov = await p.evaluate(() => document.documentElement.scrollWidth > innerWidth);
	await p.screenshot({ path: `shots/plan_compare_${w}.png` });
	console.log(w, { cards: n, badge, pageOverflow: ov, errs });
	if (n < 2 || errs.length) bad++;
}
await b.close();
process.exit(bad ? 1 : 0);
