// 오류/빈 분기에도 h1 이 있어야 한다(AUD-4eee31) — 소스 정적 검사.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const src = (p) => readFileSync(new URL(`../src/routes/${p}/+page.svelte`, import.meta.url), 'utf8');

test('coach 스레드 오류 분기에 h1', () => {
	assert.match(src('coach/[threadId]'), /<h1 class="sr-only">Coach 대화<\/h1>/);
});
test('소스 상세 오류·미존재 분기에 h1', () => {
	assert.match(src('data/sources/[provider]'), /data\.notFound \|\| !d \|\| !line\}\s*<h1 class="sr-only">\{syncProviderName\(data\.provider\)\}<\/h1>/);
});
test('랩 실패·빈 분기에 h1', () => {
	assert.match(src('library/[id]/laps'), /data\.laps\.length === 0\}\s*<h1 class="sr-only">랩<\/h1>/);
});
