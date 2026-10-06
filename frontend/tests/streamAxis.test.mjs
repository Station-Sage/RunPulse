// frontend/tests/streamAxis.test.mjs
// streamAxis.ts 순수 함수 단위 테스트 — 실행: npm run test:unit (Node 내장 test runner)
import test from 'node:test';
import assert from 'node:assert/strict';
import { indexAtFraction, axisTicks, formatElapsed, streamSeconds, isTrustedBasis, distanceTicks, dotTopPct } from '../src/lib/streamAxis.ts';

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

// ── streamSeconds ─────────────────────────────────────────────────────────────

test('streamSeconds: 빈 배열 → []', () => {
	assert.deepEqual(streamSeconds([], 3600), []);
});

test('streamSeconds: totalSec=0 → null을 0으로 대체', () => {
	assert.deepEqual(streamSeconds([0, 60, null], 0), [0, 60, 0]);
});

test('streamSeconds: n=1 → [0]', () => {
	assert.deepEqual(streamSeconds([500], 3600), [0]);
});

test('streamSeconds: 유효한 elapsed_sec(lastSec >= 90% totalSec) → 원본 반환', () => {
	// totalSec=3600, lastSec=3300 → 3300/3600 = 91.7% ≥ 90%
	const elapsed = [0, 1000, 2000, 3300];
	const result = streamSeconds(elapsed, 3600);
	assert.deepEqual(result, [0, 1000, 2000, 3300]);
});

test('streamSeconds: lastSec 정확히 90% → 원본 반환', () => {
	const elapsed = [0, 1800, 3240]; // 3240/3600 = 90%
	const result = streamSeconds(elapsed, 3600);
	assert.deepEqual(result, [0, 1800, 3240]);
});

test('streamSeconds: lastSec < 90% → 등간격 환산', () => {
	// Garmin downsample 케이스: elapsed=[0,1,2,...,1691], totalSec=8357
	// 1691/8357 ≈ 20.2% < 90% → 등간격 재환산
	const n = 1692;
	const elapsed = Array.from({ length: n }, (_, i) => i); // 0..1691
	const totalSec = 8357;
	const result = streamSeconds(elapsed, totalSec);
	assert.equal(result.length, n);
	assert.equal(result[0], 0);
	assert.equal(result[n - 1], totalSec);
	// 중간 값이 선형 보간인지 확인
	const mid = result[Math.round((n - 1) / 2)];
	assert.ok(mid > totalSec * 0.4 && mid < totalSec * 0.6, `중간값 ${mid}이 전체의 40~60%여야 함`);
});

test('streamSeconds: lastSec < 90% → null은 0으로 대체 후 환산', () => {
	// null이 섞인 짧은 배열
	const elapsed = [null, null, 2]; // lastSec=2, totalSec=100 → 재환산
	const result = streamSeconds(elapsed, 100);
	assert.equal(result.length, 3);
	assert.equal(result[0], 0);
	assert.equal(result[2], 100);
});

test('streamSeconds: 재환산 결과는 단조증가', () => {
	const n = 100;
	const elapsed = Array.from({ length: n }, (_, i) => i); // lastSec=99, totalSec=3600 → 재환산
	const result = streamSeconds(elapsed, 3600);
	for (let i = 1; i < result.length; i++) {
		assert.ok(result[i] >= result[i - 1], `단조증가 위반: [${i-1}]=${result[i-1]}, [${i}]=${result[i]}`);
	}
});

test('distanceTicks: 등간격 위치에 km 라벨', () => {
	const t = distanceTicks([0, 2500, 5000, 7500, 10000], 5);
	assert.deepEqual(t.map((x) => x.label), ['0.0km', '2.5km', '5.0km', '7.5km', '10km']);
	assert.equal(t[4].frac, 1);
	assert.deepEqual(distanceTicks([]), []);
});

test('dotTopPct: min–max 선형, invert 시 위아래 반전', () => {
	assert.equal(dotTopPct([0, 10], 10, false), 0);
	assert.equal(dotTopPct([0, 10], 10, true), 100);
	assert.equal(dotTopPct([5, 5], 5, false), 50);
	assert.equal(dotTopPct([null], 1, false), null);
	assert.equal(dotTopPct([0, 10], null, false), null);
});

// ── streamSeconds: 서버 time_basis (U18d) ────────────────────────────────────

test('streamSeconds: measured basis → 짧은 마지막 값도 재환산하지 않는다', () => {
	assert.deepEqual(streamSeconds([0, 100, 200], 1000, 'measured'), [0, 100, 200]);
});

test('streamSeconds: unknown/미지정 basis → 기존 휴리스틱 유지', () => {
	assert.deepEqual(streamSeconds([0, 1, 2], 1000, 'unknown'), [0, 500, 1000]);
	assert.deepEqual(streamSeconds([0, 1, 2], 1000), [0, 500, 1000]);
});

test('streamSeconds: trusted basis 는 null 을 0 으로 대체', () => {
	assert.deepEqual(streamSeconds([null, 5], 1000, 'scaled'), [0, 5]);
	assert.equal(isTrustedBasis('derived'), true);
	assert.equal(isTrustedBasis('unknown'), false);
});
