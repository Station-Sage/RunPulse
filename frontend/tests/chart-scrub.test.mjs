// §C1 ChartScrub 코어(lib/chart/scrub.ts) 순수 함수 테스트.
import test from 'node:test';
import assert from 'node:assert/strict';
import { niceTicks, clamp01, nearestIndexByFraction, axisDateLabel } from '../src/lib/chart/scrub.ts';

test('niceTicks — 1/2/2.5/5×10ⁿ 중에서 고른다', () => {
	assert.deepEqual(niceTicks(0, 100, 5), [0, 25, 50, 75, 100]);
	assert.deepEqual(niceTicks(0, 10, 4), [0, 5, 10]);
	assert.deepEqual(niceTicks(3, 3, 4), [3]);
});

test('niceTicks — 음수 범위도 처리(step은 1/2/2.5/5/10 중 하나로 반올림)', () => {
	assert.deepEqual(niceTicks(-10, 10, 4), [-10, 0, 10]);
});

test('clamp01', () => {
	assert.equal(clamp01(-0.5), 0);
	assert.equal(clamp01(1.5), 1);
	assert.equal(clamp01(0.3), 0.3);
});

test('nearestIndexByFraction — 가장 가까운 인덱스, 빈 배열은 -1', () => {
	assert.equal(nearestIndexByFraction([0, 0.25, 0.5, 0.75, 1], 0.6), 2);
	assert.equal(nearestIndexByFraction([], 0.5), -1);
});

test('axisDateLabel — 기간 길이에 따라 형식이 바뀐다', () => {
	assert.equal(axisDateLabel('2026-09-12', 14), '9/12');
	assert.equal(axisDateLabel('2026-07-01', 90, true), '7월');
	assert.equal(axisDateLabel('2026-07-15', 90, false), '');
	assert.equal(axisDateLabel('2025-10-03', 365), '25.10');
});
