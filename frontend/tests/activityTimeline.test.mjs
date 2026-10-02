import { test } from 'node:test';
import assert from 'node:assert/strict';
import { trackDomain, yFraction, linePath, distanceTicks, flatNote, meanOf } from '../src/lib/chart/activityTimeline.ts';

test('trackDomain: 최소 폭 보장·빈 값', () => {
	assert.deepEqual(trackDomain([100, 105], 30), { min: 87.5, max: 117.5 });
	assert.deepEqual(trackDomain([1, null, 5]), { min: 1, max: 5 });
	assert.equal(trackDomain([null, null]), null);
});

test('yFraction: invert이면 큰 값이 아래', () => {
	const d = { min: 300, max: 400 };
	assert.equal(yFraction(300, d, true), 0);
	assert.equal(yFraction(400, d, true), 1);
	assert.equal(yFraction(400, d), 0);
});

test('linePath: null에서 끊김', () => {
	const p = linePath([1, 2, null, 2], { min: 1, max: 2 }, 30, 10);
	assert.equal((p.match(/M/g) ?? []).length, 2);
	assert.equal(linePath([null], { min: 0, max: 1 }, 10, 10), '');
});

test('distanceTicks: 10km 이하 1km, 초과 5km', () => {
	assert.deepEqual(distanceTicks(3500), [0, 1000, 2000, 3000]);
	assert.deepEqual(distanceTicks(21000), [0, 5000, 10000, 15000, 20000]);
	assert.deepEqual(distanceTicks(0), []);
});

test('flatNote·meanOf', () => {
	assert.equal(flatNote([10, 12, null], 5.2), '거의 평지 · 누적 상승 5m');
	assert.equal(flatNote([10, 40], 30), null);
	assert.equal(meanOf([2, null, 4]), 3);
	assert.equal(meanOf([]), null);
});
