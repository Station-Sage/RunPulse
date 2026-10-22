// §C3.3 드릴다운 URL 스택(lib/drillStackCore.ts) 순수 함수 테스트.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
	parseDrillStack,
	parseDrillToken,
	formatDrillToken,
	tokenSlug,
	resolveDrillScope,
	DRILL_MAX_DEPTH,
	isSpecialToken,
	closePlan
} from '../src/lib/drillStackCore.ts';

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

test('parseDrillToken — scope 없으면 slug만', () => {
	assert.deepEqual(parseDrillToken('m.tsb'), { slug: 'tsb' });
});

test('parseDrillToken — D1d @scope 토큰 파싱', () => {
	assert.deepEqual(parseDrillToken('m.tsb@2026-09-12'), { slug: 'tsb', scope: '2026-09-12' });
});

test('parseDrillToken — m. 접두어 없어도 동작', () => {
	assert.deepEqual(parseDrillToken('ctl@2026-01-01'), { slug: 'ctl', scope: '2026-01-01' });
});

test('formatDrillToken — scope 없으면 m.slug만', () => {
	assert.equal(formatDrillToken('tsb'), 'm.tsb');
});

test('formatDrillToken — scope 있으면 @ 붙인다', () => {
	assert.equal(formatDrillToken('tsb', '2026-09-12'), 'm.tsb@2026-09-12');
});

test('formatDrillToken ↔ parseDrillToken 왕복', () => {
	assert.deepEqual(parseDrillToken(formatDrillToken('utrs', '2026-01-05')), {
		slug: 'utrs',
		scope: '2026-01-05'
	});
});

test('resolveDrillScope — @a{id}는 activity scope, 날짜는 기본 종류 유지', () => {
	assert.deepEqual(resolveDrillScope('a17414', 'daily', '2026-09-12'), { scopeType: 'activity', scopeId: '17414' });
	assert.deepEqual(resolveDrillScope('2026-09-01', 'daily', '2026-09-12'), { scopeType: 'daily', scopeId: '2026-09-01' });
	assert.deepEqual(resolveDrillScope(undefined, 'daily', '2026-09-12'), { scopeType: 'daily', scopeId: '2026-09-12' });
	assert.equal(parseDrillToken('m.trimp@a17414').scope, 'a17414');
});

test('x. 특수 토큰: isSpecialToken · 포맷/파싱 왕복', () => {
	assert.equal(isSpecialToken('x.taper'), true);
	assert.equal(isSpecialToken('m.utrs'), false);
	assert.equal(formatDrillToken('x.taper'), 'x.taper');
	assert.equal(parseDrillToken('x.taper').slug, 'x.taper');
});

test('closePlan — 앱에서 연 1단은 back 1, 쿼리 정리 없음', () => {
	assert.deepEqual(closePlan(['m.a'], []), { back: 1, replace: null });
});

test('closePlan — 앱에서 3단 push 하면 back 3', () => {
	assert.deepEqual(closePlan(['m.a', 'm.b', 'm.c'], []), { back: 3, replace: null });
});

test('closePlan — 딥링크 2단 그대로면 history 없이 쿼리만 지운다', () => {
	assert.deepEqual(closePlan(undefined, ['m.a', 'm.b']), { back: 0, replace: [] });
});

test('closePlan — 딥링크 2단 위에 1단 push 하면 back 1 후 쿼리 정리', () => {
	assert.deepEqual(closePlan(['m.a', 'm.b', 'm.c'], ['m.a', 'm.b']), { back: 1, replace: [] });
});

test('closePlan — 딥링크 중에 새로 연 드릴(openDrill)은 back 1 후 쿼리 정리', () => {
	assert.deepEqual(closePlan(['m.x'], ['m.a', 'm.b']), { back: 1, replace: [] });
});

test('closePlan — 스택이 없으면 아무것도 하지 않는다', () => {
	assert.deepEqual(closePlan(undefined, []), { back: 0, replace: null });
});
