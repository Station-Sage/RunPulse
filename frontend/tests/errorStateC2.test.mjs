// C2 오류 상태 계약 ratchet(AUD-ad4267) — 화면이 API 실패를 ErrorState(다시 시도)로 그리고 빈 상태와 문구를 분리한다. 소스 정적 검사.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (p) => readFileSync(new URL(`../src/routes/${p}`, import.meta.url), 'utf8');

test('today/month — 실패는 ErrorState + 다시 시도, 빈 상태는 별도 문구', () => {
	const s = read('today/month/[ym]/+page.svelte');
	assert.match(s, /\{:else if failure\}\s*<ErrorState \{failure\} onRetry=\{loadNarrative\} \/>/);
	assert.match(s, /data-testid="month-empty"/);
	assert.doesNotMatch(s, /error \|\| !narrativeData/);
});

test('library/wellness/[date] — 서버 오류 분기가 ErrorState + 다시 시도', () => {
	const s = read('library/wellness/[date]/+error.svelte');
	assert.match(s, /<ErrorState [^>]*onRetry=\{\(\) => invalidateAll\(\)\}/);
	assert.doesNotMatch(s, /잠시 후 다시 시도해 주세요/);
});
