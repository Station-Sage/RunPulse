// /demo 스냅샷 생성 — synth 서버를 크롤링해 GET /api/v1 응답을 키별로 모아 frontend/static/demo/snapshot.json에 쓴다.
// 사용: BASE=http://127.0.0.1:18999 node export_demo_snapshot.mjs
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'node:fs';

const BASE = process.env.BASE;
const OUT = new URL('../../../frontend/static/demo/snapshot.json', import.meta.url);
const snap = {};
const key = (u) => {
	const x = new URL(u);
	const p = x.pathname.slice('/api/v1'.length);
	const q = [...x.searchParams.entries()].sort(([a], [b]) => a.localeCompare(b));
	return q.length ? `${p}?${new URLSearchParams(q)}` : p;
};
const b = await chromium.launch();
const p = await (await b.newContext({ viewport: { width: 1100, height: 900 } })).newPage();
p.on('response', async (r) => {
	const u = r.url();
	if (!u.includes('/api/v1/') || r.request().method() !== 'GET' || !r.ok()) return;
	if (u.includes('/events') || (r.headers()['content-type'] || '').includes('event-stream')) return;
	try { snap[key(u)] = await r.json(); } catch {}
});
const visit = async (path) => { await p.goto(`${BASE}/v2${path}`, { waitUntil: 'networkidle' }); await p.waitForTimeout(600); };

await visit('/today');
for (const g of await p.locator('[data-testid^=gauge], button:has-text("UTRS"), button:has-text("CIRS"), button:has-text("TSB")').all()) {
	await g.click({ timeout: 2000 }).catch(() => {}); await p.waitForTimeout(500);
}
await visit('/library');
await visit('/library/activities');
const ids = (await (await fetch(`${BASE}/api/v1/library/activities?page=1&per_page=40`)).json())
	.data.activities.map((x) => x.id).slice(0, 4);
for (const id of ids) {
	for (const sub of ['', '/laps', '/streams', '/metrics', '/providers']) await visit(`/library/${id}${sub}`);
}
for (const slug of ['utrs', 'cirs', 'tsb', 'ctl']) await visit(`/library/metrics/${slug}`);
await visit('/library/wellness');
await visit('/coach');
const th = await p.locator('a[href*="/coach/"]').evaluateAll((as) => as.map((a) => a.getAttribute('href')));
for (const h of [...new Set(th)].filter((h) => /\/coach\/\d+/.test(h)).slice(0, 2)) await p.goto(`${BASE}${h}`, { waitUntil: 'networkidle' });
await b.close();
mkdirSync(new URL('./', OUT), { recursive: true });
writeFileSync(OUT, JSON.stringify(snap));
console.log('keys', Object.keys(snap).length);
console.log(Object.keys(snap).join('\n'));
