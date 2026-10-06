import { test } from 'node:test';
import assert from 'node:assert/strict';
import { commonRange, xFraction, nearestPoint, changeLabel, periodChange } from '../src/lib/trendChart.ts';

const S = (key, values) => ({
	key,
	label: key,
	color: '#000',
	points: values.map((v, i) => ({ date: `2026-09-${String(i + 1).padStart(2, '0')}`, value: v }))
});

test('commonRange: 두 시리즈를 한 범위로 묶고 여백을 둔다', () => {
	const r = commonRange([S('a', [10, 20]), S('b', [50, 100])]);
	assert.ok(r.min < 10);
	assert.ok(r.max > 100);
});

test('commonRange: 0 이상 데이터는 y 최소가 음수로 내려가지 않는다', () => {
	assert.equal(commonRange([S('a', [0.5, 40])]).min, 0); // 0.5 - 1.975 < 0 → 0으로 clamp
	assert.equal(commonRange([S('a', [0, 40])]).min, 0);
});

test('commonRange: 빈 입력은 null', () => {
	assert.equal(commonRange([]), null);
	assert.equal(commonRange([S('a', [])]), null);
});

test('commonRange: 값이 전부 같아도 폭이 있다', () => {
	const r = commonRange([S('a', [5, 5])]);
	assert.ok(r.max - r.min > 0);
});

test('xFraction: 구간 내 위치·clamp·길이 0', () => {
	assert.equal(xFraction('2026-09-15', '2026-09-01', '2026-09-29'), 0.5);
	assert.equal(xFraction('2026-08-01', '2026-09-01', '2026-09-29'), 0);
	assert.equal(xFraction('2026-10-30', '2026-09-01', '2026-09-29'), 1);
	assert.equal(xFraction('2026-09-01', '2026-09-01', '2026-09-01'), 0);
});

test('nearestPoint: 가장 가까운 날짜의 점', () => {
	const pts = [
		{ date: '2026-09-01', value: 1 },
		{ date: '2026-09-15', value: 2 },
		{ date: '2026-09-29', value: 3 }
	];
	assert.equal(nearestPoint(pts, 0.55, '2026-09-01', '2026-09-29').date, '2026-09-15');
	assert.equal(nearestPoint([], 0.5, '2026-09-01', '2026-09-29'), null);
});

test('changeLabel: 작은 기준값은 절대 변화, 큰 기준값은 퍼센트', () => {
	const small = [
		{ date: '2026-08-20', value: 4.5 },
		{ date: '2026-09-19', value: 37.9 }
	];
	assert.equal(changeLabel(small), '+33.4');
	const big = [
		{ date: '2026-08-20', value: 50 },
		{ date: '2026-09-19', value: 60 }
	];
	assert.equal(changeLabel(big), '+20.0%');
	assert.equal(changeLabel([]), '—');
	const down = [
		{ date: '2026-08-20', value: 60 },
		{ date: '2026-09-19', value: 50 }
	];
	assert.equal(changeLabel(down), '-16.7%');
});

test('changeLabel: 30일보다 최근 점만 있으면 첫 점 기준', () => {
	const pts = [
		{ date: '2026-09-10', value: 20 },
		{ date: '2026-09-19', value: 22 }
	];
	assert.equal(changeLabel(pts), '+10.0%');
});

import { movingAverage, splitOnGaps, spanRange, trendAriaLabel } from '../src/lib/trendChart.ts';

test('movingAverage: 7일 창 평균, 창 밖 점은 제외', () => {
	const pts = [
		{ date: '2026-09-01', value: 10 },
		{ date: '2026-09-02', value: 20 },
		{ date: '2026-09-20', value: 30 }
	];
	const ma = movingAverage(pts);
	assert.equal(ma[1].value, 15);
	assert.equal(ma[2].value, 30);
});

test('splitOnGaps: 2일 초과 공백에서 끊는다', () => {
	const mk = (d) => ({ date: d, value: 1 });
	const parts = splitOnGaps([mk('2026-09-01'), mk('2026-09-03'), mk('2026-09-07')]);
	assert.deepEqual(parts.map((p) => p.length), [2, 1]);
	assert.deepEqual(splitOnGaps([]), []);
});

test('spanRange: 최소 폭 미만이면 중심 기준 확장, 이상이면 그대로', () => {
	assert.deepEqual(spanRange(60, 62, 10), { min: 56, max: 66 });
	assert.deepEqual(spanRange(0, 20, 10), { min: 0, max: 20 });
});

test('trendAriaLabel: 현재·최고·최저 요약과 빈 데이터', () => {
	const pts = [
		{ date: '2026-08-08', value: 89 },
		{ date: '2026-09-01', value: 37 },
		{ date: '2026-10-01', value: 60 }
	];
	assert.equal(trendAriaLabel('UTRS', '3개월', pts), 'UTRS 3개월: 현재 60, 최고 89(8월 8일), 최저 37(9월 1일)');
	assert.match(trendAriaLabel('UTRS', '3개월', []), /데이터 없음/);
});

test('weekTicks: 구간 내 월요일만', async () => {
	const { weekTicks } = await import('../src/lib/trendChart.ts');
	assert.deepEqual(weekTicks('2026-09-04', '2026-10-03'), ['2026-09-07', '2026-09-14', '2026-09-21', '2026-09-28']);
	assert.deepEqual(weekTicks('', ''), []);
});

test('dateAtOffset: 월 경계를 넘는 일 단위 오프셋', async () => {
	const { dateAtOffset } = await import('../src/lib/trendChart.ts');
	assert.equal(dateAtOffset('2026-09-28', 0), '2026-09-28');
	assert.equal(dateAtOffset('2026-09-28', 5), '2026-10-03');
});

test('periodChange: 첫 점→끝 점 변화와 퍼센트, 점 부족·0 기준 처리', () => {
	const pts = S('a', [50, 55, 44]).points;
	const r = periodChange(pts);
	assert.equal(r.delta, -6);
	assert.ok(Math.abs(r.pct - -12) < 1e-9);
	assert.equal(periodChange(pts.slice(0, 1)), null);
	assert.equal(periodChange(S('a', [0, 3]).points).pct, null);
});

test('monthTicks: 매월 1일, quarterly는 분기 첫 달만', async () => {
	const { monthTicks } = await import('../src/lib/trendChart.ts');
	assert.deepEqual(monthTicks('2026-07-15', '2026-10-05'), ['2026-08-01', '2026-09-01', '2026-10-01']);
	assert.deepEqual(monthTicks('2025-10-05', '2026-10-05', true), ['2026-01-01', '2026-04-01', '2026-07-01', '2026-10-01']);
	assert.deepEqual(monthTicks('', ''), []);
});

import { eventSymbol, markerEvents } from '../src/lib/trendChart.ts';
import test2 from 'node:test';
import assert2 from 'node:assert/strict';

test2('eventSymbol: 종류별 기호', () => {
	assert2.equal(eventSymbol('version_change'), '◆');
	assert2.equal(eventSymbol('basis_change'), '◇');
	assert2.equal(eventSymbol('race'), '▲');
});

test2('markerEvents: 같은 날 ◆ > ◇ > ▲ 우선, 범위 밖 제외', () => {
	const ev = [
		{ date: '2026-09-26', kind: 'race', label: 'r' },
		{ date: '2026-09-26', kind: 'version_change', label: 'v' },
		{ date: '2026-09-26', kind: 'basis_change', label: 'b' },
		{ date: '2026-08-01', kind: 'race', label: 'old' },
	];
	const m = markerEvents(ev, '2026-09-01', '2026-10-01');
	assert2.equal(m.length, 1);
	assert2.equal(m[0].kind, 'version_change');
});
