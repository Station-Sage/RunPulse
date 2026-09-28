// §C3.3 드릴다운 URL 스택(lib/drillStackCore.ts) 순수 함수 테스트.
import test from 'node:test';
import assert from 'node:assert/strict';
import { parseDrillStack, tokenSlug, DRILL_MAX_DEPTH } from '../src/lib/drillStackCore.ts';

test('parseDrillStack — drill 파라미터 없으면 빈 배열', () => {
	assert.deepEqual(parseDrillStack(new URL('https://x/y')), []);
});

test('parseDrillStack — 쉼표로 이은 토큰을 순서대로 반환', () => {
	assert.deepEqual(
		parseDrillStack(new URL('https://x/y?drill=m.tsb,m.ctl')),
		['m.tsb', 'm.ctl']
	);
});

test('parseDrillStack — 빈 토큰·공백은 제거', () => {
	assert.deepEqual(parseDrillStack(new URL('https://x/y?drill=m.tsb,, m.ctl ')), ['m.tsb', 'm.ctl']);
});

test('tokenSlug — m. 접두어를 벗긴다', () => {
	assert.equal(tokenSlug('m.ctl'), 'ctl');
});

test('tokenSlug — 접두어 없으면 그대로', () => {
	assert.equal(tokenSlug('ctl'), 'ctl');
});

test('DRILL_MAX_DEPTH — 스택 최대 3단(§C3.1)', () => {
	assert.equal(DRILL_MAX_DEPTH, 3);
});
