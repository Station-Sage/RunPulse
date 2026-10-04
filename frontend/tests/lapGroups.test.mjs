import test from 'node:test';
import assert from 'node:assert/strict';
import { classifyIntervals, divergence, lapPace } from '../src/lib/lapGroups.ts';

const lap = (pace) => ({ avg_pace_sec_km: pace, distance_m: 1000, duration_sec: pace });

test('lapPace: avg_pace 우선, 없으면 거리·시간으로 계산', () => {
	assert.equal(lapPace({ avg_pace_sec_km: 300 }), 300);
	assert.equal(lapPace({ avg_pace_sec_km: null, distance_m: 500, duration_sec: 150 }), 300);
	assert.equal(lapPace({ avg_pace_sec_km: null, distance_m: null, duration_sec: 150 }), null);
});

test('classifyIntervals: 워크/회복 번갈아 나오면 인터벌', () => {
	const laps = [330, 270, 420, 270, 420, 270, 420, 330].map(lap);
	const r = classifyIntervals(laps);
	assert.ok(r);
	assert.equal(r.roles[1], 'work');
	assert.equal(r.roles[2], 'recovery');
	assert.equal(Math.round(r.workAvg), 294);
	assert.equal(Math.round(r.recoveryAvg), 420);
});

test('classifyIntervals: 일정 페이스·랩 부족은 null', () => {
	assert.equal(classifyIntervals([300, 301, 299, 300, 302].map(lap)), null);
	assert.equal(classifyIntervals([270, 420, 270].map(lap)), null);
	assert.equal(classifyIntervals([270, 270, 270, 420, 420, 420].map(lap)), null);
});

test('divergence: ±30초 클램프, 빠름=+', () => {
	assert.equal(divergence(270, 300), 1);
	assert.equal(divergence(330, 300), -1);
	assert.equal(divergence(285, 300), 0.5);
	assert.equal(divergence(null, 300), 0);
});
