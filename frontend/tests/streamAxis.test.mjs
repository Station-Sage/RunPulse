// frontend/tests/streamAxis.test.mjs
// streamAxis.ts 순수 함수 단위 테스트 — 실행: npm run test:unit (Node 내장 test runner)
import test from 'node:test';
import assert from 'node:assert/strict';
import { indexAtFraction, axisTicks, formatElapsed } from '../src/lib/streamAxis.ts';

// ── indexAtFraction ──────────────────────────────────────────────────────────

test('indexAtFraction: fraction=0 → 0', () => {
	assert.equal(indexAtFraction(100, 0), 0);
});

test('indexAtFraction: fraction=1 → n-1', () => {
	assert.equal(indexAtFraction(100, 1), 99);
});

test('indexAtFraction: fraction=0.5 → 중간 인덱스', () => {
	// round(0.5 * 99) = round(49.5) = 50
	assert.equal(indexAtFraction(100, 0.5), 50);
});

test('indexAtFraction: n=0 → 0', () => {
	assert.equal(indexAtFraction(0, 0.5), 0);
});

test('indexAtFraction: n=1 → 0 항상', () => {
	assert.equal(indexAtFraction(1, 0), 0);
	assert.equal(indexAtFraction(1, 1), 0);
	assert.equal(indexAtFraction(1, 0.5), 0);
});

test('indexAtFraction: 범위 초과 fraction은 클램프', () => {
	assert.equal(indexAtFraction(10, -1), 0);
	assert.equal(indexAtFraction(10, 2), 9);
});

// ── formatElapsed ────────────────────────────────────────────────────────────

test('formatElapsed: 0 → "0"', () => {
	assert.equal(formatElapsed(0), '0');
});

test('formatElapsed: null → "—"', () => {
	assert.equal(formatElapsed(null), '—');
});

test('formatElapsed: undefined → "—"', () => {
	assert.equal(formatElapsed(undefined), '—');
});

test('formatElapsed: 900 → "15m"', () => {
	assert.equal(formatElapsed(900), '15m');
});

test('formatElapsed: 3300 → "55m"', () => {
	assert.equal(formatElapsed(3300), '55m');
});

test('formatElapsed: 3600 → "1h 00m"', () => {
	assert.equal(formatElapsed(3600), '1h 00m');
});

test('formatElapsed: 3660 → "1h 01m"', () => {
	assert.equal(formatElapsed(3660), '1h 01m');
});

test('formatElapsed: 소수점은 반올림', () => {
	assert.equal(formatElapsed(899.6), '15m');
});

// ── axisTicks ─────────────────────────────────────────────────────────────────

test('axisTicks: 빈 배열 → []', () => {
	assert.deepEqual(axisTicks([], 5), []);
});

test('axisTicks: count < 2 → []', () => {
	assert.deepEqual(axisTicks([0, 60, 120], 1), []);
});

test('axisTicks: 3개 눈금 — frac 0/0.5/1', () => {
	const elapsed = Array.from({ length: 101 }, (_, i) => i * 30); // 0..3000
	const ticks = axisTicks(elapsed, 3);
	assert.equal(ticks.length, 3);
	assert.equal(ticks[0].frac, 0);
	assert.equal(ticks[1].frac, 0.5);
	assert.equal(ticks[2].frac, 1);
});

test('axisTicks: 첫 눈금 라벨 = "0" (elapsed=0)', () => {
	const elapsed = Array.from({ length: 100 }, (_, i) => i * 33);
	const ticks = axisTicks(elapsed, 5);
	assert.equal(ticks[0].label, '0');
});

test('axisTicks: null elapsed_sec는 이웃 non-null 값으로 대체', () => {
	// 인덱스 0이 null → nearestNonNull → 300(인덱스 2)
	const elapsed = [null, null, 300, null, null];
	const ticks = axisTicks(elapsed, 3);
	assert.equal(ticks[0].label, '5m');
});
