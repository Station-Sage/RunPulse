// 감사 스윕(기계 감지) — jobs 파일의 각 셀을 방문해 결함 후보를 JSON 으로 출력한다. 사용: node sweep_pw.mjs <jobs.json>
// jobs: {base, viewport:{width,height}, state, jobs:[{cell,path}]}. 환경: PW_CHROMIUM(없으면 기본 탐색)
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require('../synth_smoke/pw/node_modules/playwright');

const cfg = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const exe = process.env.PW_CHROMIUM || (['/opt/pw-browsers/chromium'].find((p) => { try { readFileSync(p); return true; } catch { return false; } }));
const b = await chromium.launch(exe ? { executablePath: exe } : {});
const ctx = await b.newContext({ viewport: cfg.viewport, locale: 'ko-KR' });
if (cfg.state === 'error') {
	await ctx.route(/\/api\//, (r) => r.fulfill({ status: 500, contentType: 'application/json', body: '{"error":{"code":"X","message":"x"}}' }));
}
const LEAK = /\bundefined\b|\bNaN\b|\[object Object\]|\bnull\b/;
const out = [];
for (const { cell, path } of cfg.jobs) {
	const page = await ctx.newPage();
	const issues = [];
	page.on('pageerror', (e) => issues.push(`pageerror: ${e.message.slice(0, 120)}`));
	page.on('console', (m) => { if (m.type() === 'error' && !/favicon|status of 5\d\d|Failed to load resource/.test(m.text())) issues.push(`console: ${m.text().slice(0, 120)}`); });
	if (cfg.state !== 'error') page.on('response', (r) => { const u = new URL(r.url()); if (u.pathname.startsWith('/api/') && r.status() >= 400) issues.push(`http ${r.status()}: ${u.pathname}`); });
	try {
		await page.goto(cfg.base + '/v2' + path, { waitUntil: 'load', timeout: 20000 });
		await page.waitForLoadState('networkidle', { timeout: 6000 }).catch(() => {});
		await page.waitForTimeout(500);
		const d = await page.evaluate(() => {
			const vis = (e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
			const main = document.querySelector('main') || document.body;
			const small = [...document.querySelectorAll('button, a[href], [role=button]')].filter(vis).filter((e) => getComputedStyle(e).display !== 'inline').filter((e) => { const r = e.getBoundingClientRect(); return r.width > 1 && r.height > 1 && (r.height < 24 || r.width < 24); }).length;
			return {
				overflow: document.documentElement.scrollWidth - window.innerWidth,
				text: main.innerText || '',
				body: document.body.innerText || '',
				h1: document.querySelectorAll('h1').length,
				brokenImg: [...document.images].filter((i) => i.complete && i.naturalWidth === 0 && vis(i)).length,
				errorState: document.querySelectorAll('[data-testid=error-state]').length,
				small,
			};
		});
		if (d.overflow > 1) issues.push(`overflow-x: ${d.overflow}px`);
		if (d.text.trim().length < 5) issues.push('blank-main');
		const leak = d.body.match(LEAK);
		if (leak) issues.push(`text-leak: ${leak[0]}`);
		if (d.brokenImg) issues.push(`broken-img: ${d.brokenImg}`);
		if (d.small) issues.push(`tap-target<24px: ${d.small}`);
		if (!d.h1) issues.push('no-h1');
		if (cfg.state === 'error' && !d.errorState) issues.push('error-state-missing');
	} catch (e) {
		issues.push(`nav-fail: ${String(e.message).slice(0, 100)}`);
	}
	out.push({ cell, issues });
	await page.close();
}
await b.close();
console.log(JSON.stringify(out));
