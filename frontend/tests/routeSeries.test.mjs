import test from 'node:test';
import assert from 'node:assert/strict';
import { routeFromSeries, valueFraction, mixColor, kmMarkers, nearestDistIndex, inSegment } from '../src/lib/chart/routeSeries.ts';

const series = (n, gps = true) => ({
	step_m: 100,
	dist_m: Array.from({ length: n }, (_, i) => i * 100),
	pace_sec_km: Array.from({ length: n }, (_, i) => 300 + i),
	hr: Array.from({ length: n }, () => 150),
	alt_m: Array.from({ length: n }, () => 10),
	lat: Array.from({ length: n }, (_, i) => (gps ? 37 + i * 0.001 : null)),
	lon: Array.from({ length: n }, (_, i) => (gps ? 127 + i * 0.001 : null))
});

test('GPS 없으면 null(실내)', () => {
	assert.equal(routeFromSeries(series(20, false)), null);
	assert.equal(routeFromSeries(null), null);
});

test('경로 투영과 km 마커', () => {
	const r = routeFromSeries(series(31));
	assert.ok(r);
	assert.equal(r.route.points.length, 31);
	assert.deepEqual(kmMarkers(r).map((m) => m.km), [1, 2, 3]);
});

test('색은 토큰 color-mix, hex 없음', () => {
	const c = mixColor(0.5, 'pace');
	assert.match(c, /var\(--color-delta-worse\) 50%/);
	assert.ok(!c.includes('#'));
	assert.equal(mixColor(null, 'hr'), 'var(--color-fg-muted)');
	assert.equal(valueFraction(5, { lo: 0, hi: 10 }), 0.5);
	assert.equal(valueFraction(20, { lo: 0, hi: 10 }), 1);
});

test('구간 판정·최근접', () => {
	assert.equal(nearestDistIndex([0, 100, 200], 140), 1);
	assert.ok(inSegment(1500, 2));
	assert.ok(!inSegment(1000, 2));
	assert.ok(!inSegment(500, null));
});
