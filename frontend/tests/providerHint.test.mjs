import { test } from 'node:test';
import assert from 'node:assert/strict';
import { providerHint, showSourceBadge } from '../src/lib/providerHint.ts';

const nowMs = Date.parse('2026-09-25T00:00:00Z');

test('providerHint: has_data false → 데이터 없음 문구', () => {
	const hint = providerHint({ has_data: false, last_new_data_at: null, activity_count: 0 }, 0);
	assert.ok(hint != null && hint.startsWith('데이터 없음'));
});

test('providerHint: 96일 전 동기화 → 일째 문구', () => {
	const hint = providerHint({ has_data: true, last_new_data_at: '2026-06-20T10:00:00+00:00', activity_count: 5 }, nowMs);
	assert.ok(hint != null && hint.startsWith('96일째'));
});

test('providerHint: 14일 전 동기화 → 일 전이 마지막 새 데이터예요.', () => {
	const hint = providerHint({ has_data: true, last_new_data_at: '2026-09-10T10:00:00+00:00', activity_count: 5 }, nowMs);
	assert.equal(hint, '14일 전이 마지막 새 데이터예요.');
});

test('providerHint: 1일 전 동기화 → null', () => {
	const hint = providerHint({ has_data: true, last_new_data_at: '2026-09-24T10:00:00+00:00', activity_count: 5 }, nowMs);
	assert.equal(hint, null);
});

test('showSourceBadge: 단일 소스 → false', () => {
	assert.equal(showSourceBadge(['garmin', 'garmin']), false);
});

test('showSourceBadge: 복수 소스 → true', () => {
	assert.equal(showSourceBadge(['garmin', 'strava']), true);
});

test('showSourceBadge: 빈 배열 → false', () => {
	assert.equal(showSourceBadge([]), false);
});
