// frontend/src/lib/format.ts 순수 함수 테스트 — 실행: npm run test:unit (Node 내장 test runner, 타입 스트리핑)
import test from 'node:test';
import assert from 'node:assert/strict';
import { formatRelativeTime, parseDbTimestamp } from '../src/lib/format.ts';

const dbTs = (msAgo) => new Date(Date.now() - msAgo).toISOString().slice(0, 19).replace('T', ' ');

test('SQLite UTC 타임스탬프(시간대 표기 없음)는 UTC로 해석한다', () => {
	assert.equal(parseDbTimestamp('2026-09-24 03:25:53').toISOString(), '2026-09-24T03:25:53.000Z');
});

test('시간대가 명시된 ISO는 그대로 해석한다', () => {
	assert.equal(parseDbTimestamp('2026-09-24T03:25:53Z').toISOString(), '2026-09-24T03:25:53.000Z');
	assert.equal(parseDbTimestamp('2026-09-24T12:25:53+09:00').toISOString(), '2026-09-24T03:25:53.000Z');
});

test('formatRelativeTime — 시스템 시간대와 무관하게 방금 저장된 DB 시각은 "방금 전"', () => {
	assert.equal(formatRelativeTime(dbTs(10_000)), '방금 전');
});

test('formatRelativeTime — 3시간 전·2일 전', () => {
	assert.equal(formatRelativeTime(dbTs(3 * 3600_000 + 5000)), '3시간 전');
	assert.equal(formatRelativeTime(dbTs(2 * 86400_000 + 5000)), '2일 전');
});

import { formatPaceRange } from '../src/lib/format.ts';

test('formatPaceRange — 초/km 범위를 m:ss 로(분으로 오인하지 않는다)', () => {
	assert.equal(formatPaceRange(365, 405), '6:05–6:45/km');
	assert.equal(formatPaceRange(265, null), '>4:25/km');
	assert.equal(formatPaceRange(null, 280), '<4:40/km');
	assert.equal(formatPaceRange(null, null), '');
});

import { weekProgressLabel } from '../src/lib/format.ts';

test('weekProgressLabel — 진행 중·시작 전', () => {
	assert.equal(weekProgressLabel(3, 9), '3주차 / 9주');
	assert.equal(weekProgressLabel(3, null), '3주차');
	assert.equal(weekProgressLabel(0, 6), '시작 전 (1주 뒤)');
	assert.equal(weekProgressLabel(-2, 6), '시작 전 (3주 뒤)');
});

import { formatPace } from '../src/lib/format.ts';

test('formatPace — 초를 먼저 반올림해 "5:60" 같은 표기가 나오지 않는다', () => {
	assert.equal(formatPace(359.6), '6:00/km');
	assert.equal(formatPace(356.8), '5:57/km');
	assert.equal(formatPaceRange(359.6, 419.7), '6:00–7:00/km');
});
