import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mondayOf, weekLabel, dayLabel, weekGroups } from '../src/lib/activityList.ts';

test('mondayOf: 일요일은 그 주 월요일로, 월요일은 자기 자신', () => {
	assert.equal(mondayOf('2026-09-20'), '2026-09-14'); // 일
	assert.equal(mondayOf('2026-09-14'), '2026-09-14'); // 월
	assert.equal(mondayOf('2026-09-24T07:30:00Z'), '2026-09-21'); // 목
});

test('weekLabel / dayLabel', () => {
	assert.equal(weekLabel('2026-09-14'), '9/14 – 9/20');
	assert.equal(weekLabel('2026-12-28'), '12/28 – 1/3');
	assert.equal(dayLabel('2026-09-20'), '9/20 (일)');
	assert.equal(dayLabel('2026-09-24'), '9/24 (목)');
});

const A = (d, km, sec, t = 'running') => ({ start_time: `${d}T07:00:00`, distance_m: km * 1000, duration_sec: sec, activity_type: t });

test('weekGroups: 연속된 같은 주를 묶고 러닝만 합산', () => {
	const g = weekGroups([A('2026-09-24', 10, 3600), A('2026-09-22', 5, 1800), A('2026-09-22', 3, 900, 'swimming'), A('2026-09-20', 24.2, 8000)]);
	assert.equal(g.length, 2);
	assert.equal(g[0].key, '2026-09-21');
	assert.equal(g[0].items.length, 3);
	assert.equal(g[0].runs, 2);
	assert.equal(g[0].km, 15);
	assert.equal(g[0].seconds, 5400);
	assert.equal(g[1].key, '2026-09-14');
	assert.equal(g[1].km, 24.2);
	assert.equal(g[1].year, 2026);
});

test('weekGroups: 빈 입력, null 거리/시간', () => {
	assert.deepEqual(weekGroups([]), []);
	const g = weekGroups([{ start_time: '2026-09-24T00:00:00', distance_m: null, duration_sec: null }]);
	assert.equal(g[0].km, 0);
	assert.equal(g[0].runs, 1);
});
