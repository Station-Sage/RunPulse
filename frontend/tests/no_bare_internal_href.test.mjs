// v2 내부 링크는 {base} 접두가 필수 — 맨 '/x' href 는 SPA 를 벗어나 Flask 404 (S4-34). v1 유지 경로만 허용.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

const ALLOWED = ['/training/export.ics', '/connect/garmin'];

function walk(dir) {
	return readdirSync(dir).flatMap((n) => {
		const p = join(dir, n);
		return statSync(p).isDirectory() ? walk(p) : p.endsWith('.svelte') ? [p] : [];
	});
}

test('svelte 에 {base} 없는 내부 href 가 없다', () => {
	const bad = [];
	for (const f of walk('src')) {
		readFileSync(f, 'utf8').split('\n').forEach((line, i) => {
			for (const m of line.matchAll(/href="(\/[a-z][^"]*)"/g)) {
				if (!ALLOWED.includes(m[1])) bad.push(`${f}:${i + 1} ${m[1]}`);
			}
		});
	}
	assert.deepEqual(bad, []);
});
