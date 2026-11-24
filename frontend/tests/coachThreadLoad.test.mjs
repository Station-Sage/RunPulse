// coach 스레드 load 는 Failure 채널 하나(AUD-68c84e) — notFoundFailure 단위 + 소스 정적 검사.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { notFoundFailure } from '../src/lib/loadFailure.ts';

const route = (f) => readFileSync(new URL(`../src/routes/coach/[threadId]/${f}`, import.meta.url), 'utf8');

test('notFoundFailure 는 표준 404 Failure', () => {
	assert.deepEqual(notFoundFailure('BAD_ID'), { kind: 'not_found', status: 404, code: 'BAD_ID', detail: '404 BAD_ID' });
});
test('+page.ts 는 classifyFailure·depends 를 쓰고 errorMessage 가 없다', () => {
	const s = route('+page.ts');
	assert.match(s, /classifyFailure/);
	assert.match(s, /depends\(/);
	assert.doesNotMatch(s, /errorMessage/);
});
test('+page.svelte 는 LoadFailure 를 렌더하고 액션 오류를 load 값으로 초기화하지 않는다', () => {
	const s = route('+page.svelte');
	assert.match(s, /<LoadFailure\b/);
	assert.doesNotMatch(s, /data\.errorMessage/);
	assert.match(s, /let errorMessage = \$state<string \| null>\(null\)/);
});
