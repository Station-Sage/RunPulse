import { chromium } from '/home/ubuntu/projects/RunPulse/scripts/synth_smoke/pw/node_modules/playwright/index.mjs';
const b = await chromium.launch({ executablePath: '/home/ubuntu/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome' });
const base = 'http://127.0.0.1:18205/v2';
const routes = (process.argv[2] || '/today,/library,/library/activities,/library/metrics,/library/metrics/ctl,/library/wellness,/library/providers,/coach,/coach/new,/coach/plan,/coach/plan/new,/coach/plan/compare,/coach/plan/replan,/data,/data/export,/data/import,/data/settings,/data/settings/ai,/data/settings/profile,/data/sources,/data/sync,/today/race,/today/race/calendar,/today/race/races,/welcome,/demo,/landing').split(',');
const ctx = await b.newContext({ viewport: { width: 375, height: 800 } });
await ctx.addInitScript(() => sessionStorage.setItem('runpulse.demo', '1'));
const p = await ctx.newPage();
for (const r of routes) {
	await p.goto(base + r, { waitUntil: 'networkidle' }).catch(() => {});
	const info = await p.evaluate(() => ({
		h1: [...document.querySelectorAll('h1')].map((h) => h.textContent.trim().slice(0, 20)),
		navs: document.querySelectorAll('nav[aria-label="주 메뉴"]').length,
		over: document.documentElement.scrollWidth > document.documentElement.clientWidth,
		small: [...document.querySelectorAll('a,button,input,select,[role=button]')].filter((e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && (r.height < 44 || r.width < 44) && getComputedStyle(e).visibility !== 'hidden'; }).length
	}));
	console.log(r.padEnd(28), 'h1', info.h1.length, JSON.stringify(info.h1), 'over', info.over, 'small', info.small);
}
await b.close();
