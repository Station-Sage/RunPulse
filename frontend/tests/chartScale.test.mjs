// frontend/tests/chartScale.test.mjs
// chartScale.ts 순수 함수 단위 테스트 — 실행: npm run test:unit (Node 내장 test runner)
import test from 'node:test';
import assert from 'node:assert/strict';
import { percentile, clampToPercentile, clampOutliers } from '../src/lib/chartScale.ts';

// ── percentile ──────────────────────────────────────────────────────────────

test('percentile: 빈 배열 → 0', () => {
	assert.equal(percentile([], 50), 0);
});

test('percentile: 단일 값 → 그 값 반환', () => {
	assert.equal(percentile([42], 50), 42);
	assert.equal(percentile([42], 0), 42);
	assert.equal(percentile([42], 100), 42);
});

test('percentile: p=0 → 최솟값', () => {
	assert.equal(percentile([3, 1, 4, 1, 5, 9, 2, 6], 0), 1);
});

test('percentile: p=100 → 최댓값 (마지막 요소)', () => {
	// floor(100/100 * 8) = 8 → min(8, 7) = 7 → sorted[7] = 9
	assert.equal(percentile([3, 1, 4, 1, 5, 9, 2, 6], 100), 9);
});

test('percentile: p=50 → 중앙값(nearest-rank)', () => {
	// sorted: [1,2,3,4,5], floor(50/100 * 5) = 2 → sorted[2] = 3
	assert.equal(percentile([1, 2, 3, 4, 5], 50), 3);
});

test('percentile: p=2, 100개 값 → 2번째 인덱스', () => {
	const vals = Array.from({ length: 100 }, (_, i) => i); // 0..99
	// floor(2/100 * 100) = 2 → sorted[2] = 2
	assert.equal(percentile(vals, 2), 2);
});

test('percentile: p=98, 100개 값', () => {
	const vals = Array.from({ length: 100 }, (_, i) => i); // 0..99
	// floor(98/100 * 100) = 98 → sorted[98] = 98
	assert.equal(percentile(vals, 98), 98);
});

// ── clampToPercentile ───────────────────────────────────────────────────────

test('clampToPercentile: 빈 배열 → 원본 반환, clamped=false', () => {
	const result = clampToPercentile([], 2, 98);
	assert.deepEqual(result.values, []);
	assert.equal(result.clamped, false);
});

test('clampToPercentile: null만 있는 배열 → 원본 반환, clamped=false', () => {
	const result = clampToPercentile([null, null], 2, 98);
	assert.deepEqual(result.values, [null, null]);
	assert.equal(result.clamped, false);
});

test('clampToPercentile: 범위 안 값만 있으면 clamped=false', () => {
	const vals = [5, 6, 7, 8, 9, 10];
	const result = clampToPercentile(vals, 2, 98);
	assert.equal(result.clamped, false);
});

test('clampToPercentile: 이상치 클램프 — 상위 이상치 제거', () => {
	// 0~99 + 스파이크 1000
	const vals = [...Array.from({ length: 100 }, (_, i) => i), 1000];
	const result = clampToPercentile(vals, 2, 98);
	assert.equal(result.clamped, true);
	// 마지막 요소(1000)가 클램프됨
	const last = result.values[result.values.length - 1];
	assert.ok(last != null && last < 1000, `클램프 후 값 ${last}이 1000 미만이어야 함`);
});

test('clampToPercentile: null은 그대로 유지', () => {
	const vals = [null, 5, 100, null, 200];
	const result = clampToPercentile(vals, 2, 98);
	assert.equal(result.values[0], null);
	assert.equal(result.values[3], null);
});

test('clampToPercentile: 클램프 후 값이 범위 안에 있음', () => {
	const base = Array.from({ length: 50 }, (_, i) => 300 + i); // 300..349
	const vals = [1, ...base, 9999];
	const { values } = clampToPercentile(vals, 2, 98);
	const nums = values.filter((v) => v != null);
	const mn = Math.min(...nums);
	const mx = Math.max(...nums);
	assert.ok(mn >= 1, `최솟값 ${mn}`);
	assert.ok(mx <= 9999, `최댓값 ${mx}`);
	// 이상치가 클램프돼 범위가 좁아졌는지 확인
	assert.ok(mx < 9999, `9999는 클램프됐어야 함: ${mx}`);
});

// ── clampOutliers ───────────────────────────────────────────────────────────

test('clampOutliers: 2-98% 백분위 적용', () => {
	const base = Array.from({ length: 100 }, (_, i) => 500 + i); // 정상 범위 500..599
	const vals = [4, 20, ...base, 15000]; // 하·상위 스파이크
	const { values, clamped } = clampOutliers(vals);
	assert.equal(clamped, true);
	const nums = values.filter((v) => v != null);
	assert.ok(Math.max(...nums) < 15000, '상위 스파이크가 클램프돼야 함');
});

test('clampOutliers: 이미 정상 범위이면 clamped=false', () => {
	const vals = Array.from({ length: 20 }, (_, i) => 300 + i);
	const { clamped } = clampOutliers(vals);
	assert.equal(clamped, false);
});
