import test from 'node:test';
import assert from 'node:assert/strict';
import { buildSplitRows, averagePace, divergence, fastestRow } from '../src/lib/chart/splitBars.ts';

const mk = (idx, pace, extra = {}) => ({
	idx, dist_m: 1000, moving_sec: pace, elapsed_sec: pace, stop_sec: 0,
	pace_sec_km: pace, avg_hr: 150, elev_gain_m: 2, partial: false, ...extra
});

test('21km 이하는 1km 행 그대로, partial은 거리 라벨', () => {
	const rows = buildSplitRows([mk(1, 300), mk(2, 310, { dist_m: 400, moving_sec: 124, partial: true })]);
	assert.equal(rows.length, 2);
	assert.equal(rows[1].label, '0.4');
});

test('21km 초과는 5km 묶음 + 이동시간 가중', () => {
	const splits = Array.from({ length: 22 }, (_, i) => mk(i + 1, 300));
	const rows = buildSplitRows(splits);
	assert.equal(rows.length, 5);
	assert.equal(rows[0].label, '1–5');
	assert.equal(rows[0].pace_sec_km, 300);
	assert.deepEqual(rows[4].segs, [21, 22]);
});

test('평균·최고 구간은 partial 제외', () => {
	const rows = buildSplitRows([mk(1, 300), mk(2, 320), mk(3, 200, { dist_m: 300, moving_sec: 60, partial: true })]);
	assert.equal(Math.round(averagePace(rows)), 310);
	assert.equal(fastestRow(rows), 0);
	assert.equal(averagePace([]), null);
});

test('divergence 클램프', () => {
	assert.deepEqual(divergence(300, 300), { frac: 0, clipped: false });
	assert.equal(divergence(270, 300).frac, -1);
	assert.equal(divergence(240, 300).clipped, true);
	assert.equal(divergence(null, 300).frac, 0);
});
