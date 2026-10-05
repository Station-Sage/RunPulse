import { test } from 'node:test';
import assert from 'node:assert/strict';
import { planNewHref, parsePrefill, roadmapLabel, parseKm, parseReportedLoad, reportedLoadEntries } from '../src/lib/planPrefill.ts';

test('planNewHref: target_time_sec 포함', () => {
	assert.equal(
		planNewHref('/v2', { distance_km: 42.195, race_date: '2026-10-25', target_time_sec: 15300 }),
		'/v2/coach/plan/new?distance_km=42.195&race_date=2026-10-25&target_time_sec=15300'
	);
});

test('planNewHref: target null이면 target_time_sec 없음', () => {
	const href = planNewHref('/v2', { distance_km: 42.195, race_date: '2026-10-25', target_time_sec: null });
	assert.ok(!href.includes('target_time_sec'));
});

test('parsePrefill: 정상 파라미터 파싱', () => {
	const result = parsePrefill(new URLSearchParams('distance_km=42.2&race_date=2026-10-25&target_time_sec=15300'));
	assert.equal(result.km, 42.195);
	assert.equal(result.raceDate, '2026-10-25');
	assert.equal(result.hh, '4');
	assert.equal(result.mm, '15');
	assert.equal(result.ss, '0');
});

test('parsePrefill: 표준 거리 ±1km 초과면 km null', () => {
	const result = parsePrefill(new URLSearchParams('distance_km=30'));
	assert.equal(result.km, null);
});

test('parsePrefill: 잘못된 날짜는 raceDate 빈 문자열', () => {
	const result = parsePrefill(new URLSearchParams('distance_km=42.195&race_date=bad-date'));
	assert.equal(result.raceDate, '');
});

test('roadmapLabel: 28일 이하 남은 N주', () => {
	assert.equal(roadmapLabel(28), '남은 4주 로드맵 만들기');
});

test('roadmapLabel: 30일 N주 로드맵', () => {
	assert.equal(roadmapLabel(30), '5주 로드맵 만들기');
});

test('roadmapLabel: 3일 이하 최소 1주', () => {
	assert.equal(roadmapLabel(3), '남은 1주 로드맵 만들기');
});

test('parseKm: 빈 값·범위 밖은 null, 0.1 단위 반올림', () => {
	assert.equal(parseKm('', 300), null);
	assert.equal(parseKm(null, 300), null);
	assert.equal(parseKm('0', 300), null);
	assert.equal(parseKm('301', 300), null);
	assert.equal(parseKm('abc', 300), null);
	assert.equal(parseKm('12.34', 300), 12.3);
});

test('parseReportedLoad / reportedLoadEntries: 유효한 값만', () => {
	const r = parseReportedLoad(new URLSearchParams('recent_weekly_km=15&recent_long_km=99'));
	assert.deepEqual(r, { weeklyKm: 15, longKm: null });
	assert.deepEqual(reportedLoadEntries('15', '8.5'), [['recent_weekly_km', '15'], ['recent_long_km', '8.5']]);
	assert.deepEqual(reportedLoadEntries('', '-1'), []);
});
