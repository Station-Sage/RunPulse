import test from 'node:test';
import assert from 'node:assert/strict';
import { createExplainCache } from '../src/lib/explainPrefetch.ts';

test('prefetch 후 get은 같은 요청을 재사용', async () => {
	let n = 0;
	const c = createExplainCache(async (s, d) => ({ s, d, n: ++n }));
	c.prefetch('tsb', '2026-10-01');
	const r = await c.get('tsb', '2026-10-01');
	assert.equal(r.n, 1);
	await c.get('tsb', '2026-10-02');
	assert.equal(n, 2);
});

test('TTL 경과 시 재요청, 실패는 캐시하지 않음', async () => {
	let t = 0, n = 0, fail = true;
	const c = createExplainCache(async () => { n++; if (fail) throw new Error('x'); return n; }, 100, () => t);
	await assert.rejects(c.get('a', 'd'));
	fail = false;
	await c.get('a', 'd');
	assert.equal(n, 2);
	t = 200;
	await c.get('a', 'd');
	assert.equal(n, 3);
});
