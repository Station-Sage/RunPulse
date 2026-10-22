// OVL-8 정적 가드 — 모든 role="dialog" 는 use:modal, role="alertdialog" 는 금지(role="group"+inlineConfirm).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

function walk(dir, out = []) {
	for (const n of readdirSync(dir)) {
		const p = join(dir, n);
		if (statSync(p).isDirectory()) walk(p, out);
		else if (p.endsWith('.svelte')) out.push(p);
	}
	return out;
}
const files = walk('src');

test('role="alertdialog" 없음', () => {
	const bad = files.filter((f) => readFileSync(f, 'utf8').includes('role="alertdialog"'));
	assert.deepEqual(bad, []);
});

test('role="dialog" 요소는 같은 요소에 use:modal', () => {
	const bad = [];
	for (const f of files) {
		const s = readFileSync(f, 'utf8');
		for (const m of s.matchAll(/<(\w+)\b[^<>]*?role="dialog"[^<>]*?>/gs)) {
			if (!m[0].includes('use:modal')) bad.push(f);
		}
	}
	assert.deepEqual(bad, []);
});
