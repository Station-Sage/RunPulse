// V2-AUDIT-INDIV 묶음 B2 — 활동 목록·홈·탭 순수 함수 (A-14~19, A-31, A-34~39, E-27).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { appliedCount, invalidListParams, invalidParamsNotice, parseFilters } from '../src/lib/activityFilters.ts';
import { fetchFirst, pagePlan, MAX_PER_PAGE, PER_PAGE } from '../src/lib/activityListQuery.ts';
import { rowFigures } from '../src/lib/activityRow.ts';
import { listBackPath, nextCameFromApp, rememberListQuery } from '../src/lib/activityBack.ts';
import { loadScaleNote, unitLabel } from '../src/lib/metricTabLabels.ts';
import { pointsCaption, streamRange } from '../src/lib/streamAxis.ts';

const qs = (s) => new URLSearchParams(s);

test('invalidListParams: 잘못된 page·월·정렬·날짜·종목을 골라낸다(E-27·A-19)', () => {
	assert.deepEqual(invalidListParams(qs('page=-3')), ['page']);
	assert.deepEqual(invalidListParams(qs('month=2099-99&sort=xxx&from=abc&to=2026-02-30')), ['month', 'from', 'to', 'sort']);
	assert.deepEqual(invalidListParams(qs('sport=hiit&type=nope&dist_min=-1&at=zz')), ['sport', 'type', 'dist_min', 'at']);
	assert.deepEqual(invalidListParams(qs('month=2026-09&sport=other&type=race&dist_min=21.1&sort=pace')), []);
});

test('invalidParamsNotice: 한글 이름으로 한 줄, 없으면 빈 문자열', () => {
	assert.equal(invalidParamsNotice([]), '');
	assert.equal(invalidParamsNotice(['month', 'page']), '주소의 월·페이지 값을 쓸 수 없어 빼고 보여 드려요.');
});

test('parseFilters: 쓸 수 없는 종목·유형·거리는 빼고 읽는다', () => {
	const f = parseFilters(qs('sport=hiit&type=nope&dist_min=abc&from=2026-02-30'), '2026-10-04');
	assert.equal(f.sport, '');
	assert.equal(f.type, '');
	assert.equal(f.distMin, '');
	assert.equal(f.from, undefined);
	assert.equal(f.preset, 'all');
	assert.equal(parseFilters(qs('sport=other'), '2026-10-04').sport, 'other');
});

test('appliedCount: 접힌 칩 줄의 적용 개수(A-16)', () => {
	assert.equal(appliedCount({ sport: '', type: '', distMin: '' }), 0);
	assert.equal(appliedCount({ sport: 'running', type: 'race', distMin: '' }), 2);
});

test('pagePlan: 상한 이하 한 번, 넘으면 상한 크기로 나눔(A-17)', () => {
	assert.deepEqual(pagePlan(0), []);
	assert.deepEqual(pagePlan(120), [{ page: 1, per_page: 120 }]);
	assert.deepEqual(pagePlan(440), [1, 2, 3].map((page) => ({ page, per_page: MAX_PER_PAGE })));
	assert.equal(MAX_PER_PAGE % PER_PAGE, 0);
});

test('fetchFirst: 차례로 받아 합치고 has_more=false 에서 멈춤', async () => {
	const calls = [];
	const res = await fetchFirst(600, async (p) => {
		calls.push(p.page);
		const n = p.page === 2 ? 50 : p.per_page;
		return { activities: Array.from({ length: n }, (_, i) => i), total: 250, has_more: p.page < 2 };
	});
	assert.deepEqual(calls, [1, 2]);
	assert.equal(res.activities.length, 250);
	assert.equal(res.has_more, false);
});

test('rowFigures: 수영 m·/100m, 사이클 km/h, 근력은 거리 없음, display 없으면 기존(A-31)', () => {
	const swim = rowFigures({ distance_m: 500, avg_pace_sec_km: 1342, display: { family: 'swimming', label: '수영', show_distance: true, pace: { value_sec: 120, unit: '/100m', basis: 'moving' }, speed_kmh: null, times: { moving_sec: 600, elapsed_sec: 1542 }, alt_fields: [] } });
	assert.deepEqual(swim, { distance: { value: '500', unit: 'm' }, pace: '2:00/100m' });
	const ride = rowFigures({ distance_m: 20000, display: { family: 'cycling', label: '사이클', show_distance: true, pace: null, speed_kmh: 24.5, times: {}, alt_fields: [] } });
	assert.deepEqual(ride, { distance: { value: '20.0', unit: 'km' }, pace: '24.5 km/h' });
	const lift = rowFigures({ distance_m: 0, display: { family: 'strength', label: '근력', show_distance: false, pace: null, speed_kmh: null, times: {}, alt_fields: [] } });
	assert.deepEqual(lift, { distance: null, pace: null });
	assert.deepEqual(rowFigures({ distance_m: 7140, avg_pace_sec_km: 330 }), { distance: { value: '7.1', unit: 'km' }, pace: '5:30/km' });
});

function memStore() {
	const m = new Map();
	return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)) };
}

test('listBackPath: 목록 목적지에만 기억한 필터를 붙인다(A-39)', () => {
	const st = memStore();
	assert.equal(listBackPath('/library/activities', st), '/library/activities');
	rememberListQuery('?sport=running&month=2026-09', st);
	assert.equal(listBackPath('/library/activities', st), '/library/activities?sport=running&month=2026-09');
	assert.equal(listBackPath('/library', st), '/library');
	rememberListQuery('', st);
	assert.equal(listBackPath('/library/activities', st), '/library/activities');
	assert.equal(listBackPath('/library/activities', null), '/library/activities');
});

test('nextCameFromApp: 같은 활동 탭 이동은 판단을 유지(A-39)', () => {
	const act = '/v2/library/17';
	assert.equal(nextCameFromApp(true, 'enter', null, act), false);
	assert.equal(nextCameFromApp(false, 'link', '/v2/library/activities', act), true);
	assert.equal(nextCameFromApp(true, 'link', '/v2/library/17', act), true);
	assert.equal(nextCameFromApp(true, 'link', '/v2/library/17/streams', act), true);
	assert.equal(nextCameFromApp(false, 'link', '/v2/library/17/laps', act), false);
	assert.equal(nextCameFromApp(false, 'link', '/v2/library/170', act), true);
});

test('unitLabel: 영문 단위 한글화(A-34)', () => {
	assert.equal(unitLabel('score', 'trimp'), '점');
	assert.equal(unitLabel('AU', 'relative_effort'), '');
	assert.equal(unitLabel('count', 'steps_activity'), '걸음');
	assert.equal(unitLabel('count', 'floors_climbed'), '층');
	assert.equal(unitLabel('bpm', 'max_hr'), 'bpm');
});

test('loadScaleNote: 부하 계열 2개 이상일 때만 안내(A-35)', () => {
	assert.equal(loadScaleNote(['trimp', 'max_hr']), '');
	assert.match(loadScaleNote(['trimp', 'hrss', 'training_load', 'trimp']), /^부하 지표 3개는/);
});

test('streamRange: 정수 범위, 값 없으면 —(A-37)', () => {
	assert.equal(streamRange([112.0, null, 145.4]), '112 – 145');
	assert.equal(streamRange([6.6, 10.8]), '7 – 11');
	assert.equal(streamRange([null]), '—');
});

test('pointsCaption: 소스 표준 표기 + 평균 간격(A-38)', () => {
	assert.equal(pointsCaption(['garmin', 'garmin'], 1675, 3348), 'Garmin · 기록점 1,675개(약 2초마다)');
	assert.equal(pointsCaption(['garmin', 'intervals'], 10, null), 'Garmin / Intervals · 기록점 10개');
});
