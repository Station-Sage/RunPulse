// 파일 300줄 상한 가드(ratchet) — 이미 초과한 파일은 baseline 줄 수 이하로만 허용, 새 초과 파일은 실패.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

const LIMIT = 300;
// 기존 초과 파일의 허용 줄 수(줄이면 값을 낮추고, 300 이하가 되면 항목을 지운다)
const BASELINE = { 'src/lib/types/index.ts': 1679 };

function walk(dir, out = []) {
	for (const n of readdirSync(dir)) {
		const p = join(dir, n);
		if (statSync(p).isDirectory()) walk(p, out);
		else if (/\.(svelte|ts)$/.test(p)) out.push(p);
	}
	return out;
}

test(`src 의 .svelte/.ts 는 ${LIMIT}줄 이하(baseline 예외만)`, () => {
	const bad = [];
	for (const f of walk('src')) {
		const n = readFileSync(f, 'utf8').split('\n').length - 1;
		const cap = BASELINE[f] ?? LIMIT;
		if (n > cap) bad.push(`${f}: ${n} > ${cap}`);
	}
	assert.deepEqual(bad, []);
});
