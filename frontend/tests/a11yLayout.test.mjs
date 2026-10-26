// A11Y-L 정적 가드(ratchet) — baseline(a11yLayoutBaseline.json)보다 위반이 늘면 실패, 줄면 baseline 갱신을 요구한다.
// 갱신: UPDATE_A11Y_BASELINE=1 npm run test:unit
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { CHECKS, scan } from './a11yLayoutScan.mjs';

function walk(dir, out = []) {
	for (const n of readdirSync(dir)) {
		const p = join(dir, n);
		if (statSync(p).isDirectory()) walk(p, out);
		else if (p.endsWith('.svelte')) out.push(p);
	}
	return out;
}
const BASE = new URL('./a11yLayoutBaseline.json', import.meta.url);
const current = {};
for (const f of walk('src')) {
	for (const [k, n] of Object.entries(scan(f, readFileSync(f, 'utf8')))) (current[k] ??= {})[f] = n;
}

if (process.env.UPDATE_A11Y_BASELINE) writeFileSync(BASE, JSON.stringify(current, null, '\t') + '\n');
const baseline = JSON.parse(readFileSync(BASE, 'utf8'));

for (const [k, title] of Object.entries(CHECKS)) {
	test(`A11Y-L (${k}) ${title}`, () => {
		const cur = current[k] ?? {};
		const base = baseline[k] ?? {};
		const worse = Object.keys(cur).filter((f) => cur[f] > (base[f] ?? 0)).map((f) => `${f}: ${cur[f]} > ${base[f] ?? 0}`);
		assert.deepEqual(worse, [], '새 위반 — 고치거나 설계에 맞게 처리');
		const stale = Object.keys(base).filter((f) => (cur[f] ?? 0) < base[f]);
		assert.deepEqual(stale, [], '개선됨 — UPDATE_A11Y_BASELINE=1 로 baseline 을 낮출 것');
	});
}

test('scan: 대표 위반을 잡는다', () => {
	assert.equal(scan('src/lib/x.svelte', '<p role="status" aria-live="polite">x</p>').a, 1);
	assert.equal(scan('src/lib/x.svelte', '{#if a}<p role="alert">x</p>{/if}').b, 1);
	assert.equal(scan('src/lib/x.svelte', '<p role="status">x <button>y</button></p>').c, 1);
	assert.equal(scan('src/routes/p/+page.svelte', '<div class="order-2">').d, 1);
	assert.equal(scan('src/lib/x.svelte', '<div role="dialog" aria-label="a">').f, 1);
	assert.equal(scan('src/lib/x.svelte', '<div role="dialog" aria-labelledby="a">').f, undefined);
	assert.equal(scan('src/lib/x.svelte', '<div role="group"><p role="status">x</p></div>').g, 1);
	assert.equal(scan('src/lib/x.svelte', '<p class="text-xs uppercase">S</p>').i, 1);
	assert.equal(scan('src/lib/x.svelte', '<div role="slider" tabindex="0">').j, 1);
	assert.equal(scan('src/lib/x.svelte', '<div role="slider" onkeydown={k}>').j, undefined);
});
