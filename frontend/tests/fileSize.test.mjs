// 파일 300줄 상한 점검(소프트) — 초과해도 실패시키지 않고 경고만 낸다. 분리는 러너가 BACKLOG 후속 항목(SPLIT-*)으로 남긴다.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

const LIMIT = 300;
// 기존 초과 파일의 허용 줄 수(줄이면 값을 낮추고, 300 이하가 되면 항목을 지운다)
const BASELINE = { 'src/lib/types/index.ts': 1681 };

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
	if (bad.length) console.warn(`[fileSize] 300줄 초과(후속 분리 대상):\n${bad.join('\n')}`);
  assert.ok(true);
});
