import { chromium } from '/home/ubuntu/projects/RunPulse/scripts/synth_smoke/pw/node_modules/playwright/index.mjs';
const b = await chromium.launch({ executablePath: '/home/ubuntu/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome' });
const base = 'http://127.0.0.1:18205/v2';
for (const [w, h] of [[375, 800], [1280, 800]]) {
	const ctx = await b.newContext({ viewport: { width: w, height: h } });
	await ctx.addInitScript(() => sessionStorage.setItem('runpulse.demo', '1'));
	const p = await ctx.newPage();
	for (const r of ['/today', '/library', '/coach']) {
		await p.goto(base + r, { waitUntil: 'networkidle' });
		const navs = await p.getByRole('navigation', { name: '주 메뉴' }).count();
		const over = await p.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
		console.log(w, r, 'navs', navs, 'overflow', over);
	}
	await p.goto(base + '/today', { waitUntil: 'networkidle' });
	const seq = [];
	for (let i = 0; i < 6; i++) {
		await p.keyboard.press('Tab');
		seq.push(await p.evaluate(() => (document.activeElement?.getAttribute('aria-label') || document.activeElement?.textContent || '').trim().slice(0, 14)));
	}
	console.log(w, 'tab', seq.join(' | '));
	await p.goto(base + "/today", { waitUntil: "networkidle" }); await p.keyboard.press("Tab"); await p.keyboard.press("Enter");
	console.log(w, 'after skip focus', await p.evaluate(() => document.activeElement?.id));
	await ctx.close();
}
await b.close();
