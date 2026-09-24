import { test } from 'node:test';
import assert from 'node:assert/strict';
import { xFrac, yFrac, buildFormLayout, toPolyline, nearestByFrac, OPTIMAL_BAND } from '../src/lib/formChart.ts';

const P = (d, v) => ({ date: d, value: v });
const hist = (vals, start = 1) => vals.map((v, i) => P(`2026-09-${String(start + i).padStart(2, '0')}`, v));

test('xFrac / yFrac', () => {
	assert.equal(xFrac('2026-09-15', '2026-09-01', '2026-09-29'), 0.5);
	assert.equal(xFrac('2026-09-15', '2026-09-15', '2026-09-15'), 0);
	assert.equal(yFrac(10, { min: 0, max: 10 }), 0);
	assert.equal(yFrac(0, { min: 0, max: 10 }), 1);
});

test('buildFormLayout: 빈 이력은 null', () => {
	assert.equal(buildFormLayout({ ctl: [], atl: [], tsb: [], future: [], raceDate: null }), null);
});

test('buildFormLayout: 위 패널은 0~최대×1.08, 아래 패널은 최적 밴드를 항상 포함', () => {
	const l = buildFormLayout({ ctl: hist([10, 20]), atl: hist([30, 50]), tsb: hist([-20, -30]), future: [], raceDate: null });
	assert.equal(l.top.min, 0);
	assert.ok(Math.abs(l.top.max - 54) < 1e-9);
	assert.ok(l.bottom.min < -30);
	assert.ok(l.bottom.max > OPTIMAL_BAND.hi);
	assert.equal(l.today, '2026-09-02');
	assert.equal(l.t1, '2026-09-02');
});

test('buildFormLayout: x축 끝은 레이스 날짜/예측 끝 중 늦은 날', () => {
	const f = [{ key: 'taper', label: 't', points: [P('2026-10-10', 12)] }];
	const l = buildFormLayout({ ctl: hist([10]), atl: hist([12]), tsb: hist([-2]), future: f, raceDate: '2026-10-25' });
	assert.equal(l.t1, '2026-10-25');
	assert.ok(l.bottom.max >= 30);
});

test('toPolyline / nearestByFrac', () => {
	const l = buildFormLayout({ ctl: hist([0, 10]), atl: hist([0, 10]), tsb: hist([0, 0, 0]), future: [], raceDate: null });
	const s = toPolyline(hist([0, 10]), l, l.top, 100, 50);
	assert.equal(s.split(' ').length, 2);
	assert.ok(s.startsWith('0.0,'));
	const pts = hist([1, 2, 3]);
	assert.equal(nearestByFrac(pts, 0.9, l).date, '2026-09-03');
	assert.equal(nearestByFrac([], 0.5, l), null);
});
