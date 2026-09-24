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
