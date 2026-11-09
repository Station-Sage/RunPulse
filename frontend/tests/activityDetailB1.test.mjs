// V2-AUDIT-INDIV 묶음 B1(활동 상세) 순수 함수 테스트.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
	BAD_ID_FAILURE, emptyDataNote, emptyTabs, envItems, feedbackHasInput, feedbackSummary, missingActivityView
} from '../src/lib/activityDetailView.ts';
import { headerDate, withEuro } from '../src/lib/activityHeader.ts';
import { normalizeActivityIdParam } from '../src/lib/utils/validation.ts';
import { fastestLap, isPartialLastLap, lapPaceBasisDiffers } from '../src/lib/lapGroups.ts';
import { hrCell, paceCell } from '../src/lib/activityDisplay.ts';
import { formatElevation } from '../src/lib/format.ts';
import { alignDecimals, diffText, isPauseOnlyDiff, summaryLine } from '../src/lib/providerSections.ts';

test('envItems: 반올림 0 페이스 영향 생략, 항목 없으면 빈 배열(A-06)', () => {
	assert.deepEqual(envItems({ temp_c: null, dew_point_c: null, fearp_sec_km: 330, pace_effect_sec_km: 0.4 }), []);
	assert.deepEqual(envItems({ temp_c: 21.6, dew_point_c: null, fearp_sec_km: 330, pace_effect_sec_km: 3.6 }), [
		{ label: '기온', value: '22°C' }, { label: '페이스 영향', value: '+4초/km' }
	]);
	assert.deepEqual(envItems(null), []);
});

const act = (family, source = 'intervals', siblings = []) => ({ core: { source }, siblings, display: { family } });

test('emptyDataNote: 소스 원인 + 동기화 안내, 근력은 안내만(A-05·S-16)', () => {
	const n = emptyDataNote('streams', act('running'));
	assert.match(n.reason, /Intervals에서 이 활동의 초 단위 기록/);
	assert.deepEqual(n.action, { label: '동기화 상태 보기', path: '/data/sync' });
	const s = emptyDataNote('laps', act('strength', 'garmin'));
	assert.match(s.reason, /근력 운동은 랩을/);
	assert.equal(s.action, null);
	const m = emptyDataNote('laps', act('running', 'garmin', [{ provider: 'garmin' }, { provider: 'intervals' }]));
	assert.match(m.reason, /^Garmin·Intervals에서/);
	assert.equal(emptyDataNote('laps', null).action, null);
});

test('emptyTabs: 스트림 0점·랩 없음 표시, 응답 없으면 없음(S-16)', () => {
	assert.deepEqual(emptyTabs({ stream_point_count: 0, laps: null }), ['streams', 'laps']);
	assert.deepEqual(emptyTabs({ stream_point_count: 10, laps: [{}] }), []);
	assert.deepEqual(emptyTabs(null), []);
});

test('feedbackSummary: 통증 한글, 긴 메모 자름(A-27)', () => {
	assert.equal(feedbackSummary({ rpe: 6, pain: 'mild', pain_sites: [], note: null }), 'RPE 6 · 통증 경미');
	const long = feedbackSummary({ rpe: null, pain: 'none', pain_sites: [], note: 'ㄱ'.repeat(500) });
	assert.equal(long.length, 41);
	assert.ok(long.endsWith('…'));
	assert.equal(feedbackSummary(null), '');
});

test('feedbackHasInput: 전부 비면 false(A-25)', () => {
	assert.equal(feedbackHasInput({ rpe: null, pain: null, note: '  ' }), false);
	assert.equal(feedbackHasInput({ rpe: 3, pain: null, note: '' }), true);
	assert.equal(feedbackHasInput({ rpe: null, pain: 'none', note: '' }), true);
});

test('missingActivityView: 잘못된 주소와 없는 활동 문구 구분, 장애는 null(A-24·E-28)', () => {
	assert.equal(missingActivityView(BAD_ID_FAILURE).title, '주소가 올바르지 않아요');
	assert.equal(missingActivityView({ kind: 'not_found', code: 'NOT_FOUND' }).title, '활동을 찾을 수 없어요');
	assert.equal(missingActivityView({ kind: 'network', code: 'NETWORK' }), null);
	assert.equal(missingActivityView(null), null);
});

test('headerDate: 다른 해만 연도(A-07)', () => {
	const now = new Date('2026-11-10T12:00:00');
	assert.equal(headerDate('2026-10-19T06:00:00', now), '10/19(월)');
	assert.equal(headerDate('2024-10-19T06:00:00', now), '2024. 10/19(토)');
});

test('withEuro: 받침·ㄹ받침·영문(E-28)', () => {
	assert.equal(withEuro('활동'), '활동으로');
	assert.equal(withEuro('코치'), '코치로');
	assert.equal(withEuro('오늘'), '오늘로');
	assert.equal(withEuro('Library'), 'Library로');
});

test('normalizeActivityIdParam: 숫자만, 앞자리 0은 정규화(A-21)', () => {
	assert.equal(normalizeActivityIdParam('910abc'), null);
	assert.equal(normalizeActivityIdParam('abc'), null);
	assert.equal(normalizeActivityIdParam('0'), null);
	assert.equal(normalizeActivityIdParam('-1'), null);
	assert.equal(normalizeActivityIdParam(undefined), null);
	assert.deepEqual(normalizeActivityIdParam('0910'), { id: 910, canonical: '910' });
	assert.deepEqual(normalizeActivityIdParam('17414'), { id: 17414, canonical: '17414' });
});

const lap = (distance_m, duration_sec, avg_pace_sec_km = null) => ({ distance_m, duration_sec, avg_pace_sec_km });

test('fastestLap: 자투리 마지막 랩 제외(A-08)', () => {
	const laps = [lap(1000, 360, 360), lap(1000, 344, 344), lap(1000, 350, 350), lap(298, 100, 335)];
	assert.equal(isPartialLastLap(laps, 3), true);
	assert.equal(isPartialLastLap(laps, 1), false);
	assert.deepEqual(fastestLap(laps), { pace: 344, index: 1 });
	assert.equal(fastestLap([]), null);
	// 인터벌 400m 반복은 자투리가 아니다
	const reps = [lap(400, 90, 225), lap(400, 120, 300), lap(400, 88, 220)];
	assert.equal(fastestLap(reps).index, 2);
});

test('lapPaceBasisDiffers: 시간 기준과 페이스가 1초 이상 어긋날 때(A-09)', () => {
	assert.equal(lapPaceBasisDiffers([lap(1000, 361, 362)]), true);
	assert.equal(lapPaceBasisDiffers([lap(1000, 362, 362.4)]), false);
	assert.equal(lapPaceBasisDiffers([lap(1000, 362, null)]), false);
});

test('hrCell·paceCell: 값 없으면 단위 없음, 걷기 라벨(A-04)', () => {
	assert.deepEqual(hrCell(null), { label: '평균 심박', value: '—', unit: '' });
	assert.deepEqual(hrCell(141), { label: '평균 심박', value: '141', unit: 'bpm' });
	const d = { family: 'walking', label: '걷기', show_distance: true, pace: { value_sec: 921, unit: '/km', basis: 'moving' },
		speed_kmh: null, times: { moving_sec: 1, elapsed_sec: 1 }, alt_fields: [] };
	assert.equal(paceCell(d).label, '걷기 페이스');
});

test('formatElevation: 정수 m, 1km 이상은 km(A-12)', () => {
	assert.deepEqual(formatElevation(5.3), { display: '5', unit: 'm' });
	assert.deepEqual(formatElevation(1234), { display: '1.2', unit: 'km' });
});

const row = (slug, detected, section = 'record') => ({
	slug, label: slug, unit: null, section, values: {}, diff: null,
	discrepancy: detected ? { detected: true } : null, preferredProvider: null, primaryReason: null
});

test('isPauseOnlyDiff·summaryLine: 총 시간만 다르고 이동 시간 같으면 측정 차이에서 뺀다(A-11)', () => {
	const rows = [row('duration_sec', true), row('moving_time_sec', false)];
	assert.equal(isPauseOnlyDiff(rows[0], rows), true);
	assert.equal(summaryLine(rows), '측정 차이 없음 · 총 시간은 일시정지 처리 방식이 달라요(이동 시간은 거의 같아요)');
	const both = [row('duration_sec', true), row('moving_time_sec', true)];
	assert.equal(isPauseOnlyDiff(both[0], both), false);
	assert.equal(summaryLine(both), '측정 차이 2건');
});

test('alignDecimals·diffText: 자릿수 통일, 값 하나면 —(A-12·A-13)', () => {
	assert.deepEqual(alignDecimals(['5.3', '5', '—']), ['5.3', '5.0', '—']);
	assert.deepEqual(alignDecimals(['5', '6']), ['5', '6']);
	assert.deepEqual(alignDecimals(['55:18', '57:16']), ['55:18', '57:16']);
	assert.equal(diffText(row('max_cadence', false)).text, '—');
	assert.equal(diffText(row('x', false, 'related')).text, '');
});
