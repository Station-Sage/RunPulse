import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

// SPA 최초 진입 시 from.url 이 null 이므로 `from.url.` / `from?.url.` 직접 접근은 TypeError — navFromPath 만 쓴다.
const SRC = fileURLToPath(new URL('../src', import.meta.url));
const UNSAFE = /\bfrom\??\.url\.(?!\?)/;

function walk(dir) {
	return readdirSync(dir).flatMap((n) => {
		const p = join(dir, n);
		if (statSync(p).isDirectory()) return walk(p);
		return /\.(svelte|ts|js)$/.test(n) ? [p] : [];
	});
}

test('src 에 unsafe from.url. 접근 0건', () => {
	const hits = walk(SRC).filter((f) => UNSAFE.test(readFileSync(f, 'utf8')));
	assert.deepEqual(hits, []);
});

test('month·library 레이아웃은 navFromPath 를 쓴다', () => {
	for (const f of ['routes/today/month/[ym]/+page.svelte', 'routes/library/[id]/+layout.svelte']) {
		assert.match(readFileSync(join(SRC, f), 'utf8'), /navFromPath\(/);
	}
});
