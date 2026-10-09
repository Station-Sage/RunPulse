import test from 'node:test';
import assert from 'node:assert/strict';
import * as v from '../src/lib/replanView.ts';

const W = (s, k) => ({ week_start: s, planned_km: k });
const P = (before, after) => ({ anchor_monday: '2026-10-12', before, after, external: [], preserved: [], skipped_dates: [] });

test('mergeWeeks: 정렬·한쪽만 있는 주·마지막 대회 주', () => {
	const m = v.mergeWeeks([W('2026-10-19', 40), W('2026-10-12', 50)], [W('2026-10-12', 36), W('2026-10-26', 20)]);
	assert.deepEqual(m.map((r) => r.week_start), ['2026-10-12', '2026-10-19', '2026-10-26']);
	assert.equal(m[0].delta, -14);
	assert.equal(m[1].after, null);
	assert.equal(m[2].before, null);
	assert.deepEqual(m.map((r) => r.isRace), [false, false, true]);
	assert.equal(m[0].label, '10/12 주');
});

test('deltaText', () => {
	assert.equal(deltaOf(-14), '−14');
	assert.equal(deltaOf(3.4), '+3');
	assert.equal(deltaOf(0.4), '=');
	assert.equal(deltaOf(null), '—');
});
function deltaOf(d) { return v.deltaText(d); }

test('collapseWeeks: 대회 주는 항상 보임', () => {
	const rows = v.mergeWeeks([], [1, 2, 3, 4, 5, 6].map((i) => W(`2026-10-0${i}`, i)));
	const c = v.collapseWeeks(rows);
	assert.equal(c.shown.length, 5);
	assert.equal(c.hiddenCount, 1);
	assert.equal(c.shown[4].isRace, true);
	assert.equal(v.collapseWeeks(rows, 4, true).hiddenCount, 0);
	assert.equal(v.collapseWeeks(rows.slice(0, 4)).hiddenCount, 0);
	assert.equal(v.collapseWeeks(rows.slice(0, 5)).shown.length, 5);
});

test('replanSummary: 낮춤·비슷·비었음', () => {
	assert.match(v.replanSummary(P([W('2026-10-12', 50), W('2026-10-19', 60)], [W('2026-10-12', 36), W('2026-10-19', 60)])), /36km로 낮춰/);
	assert.match(v.replanSummary(P([W('2026-10-12', 50)], [W('2026-10-12', 50.4)])), /비슷한 거리/);
	assert.match(v.replanSummary(P([W('2026-10-12', 30)], [W('2026-10-12', 40)])), /올려/);
	assert.equal(v.replanSummary(P([], [W('2026-10-12', 30), W('2026-10-19', 30)])), '대회 주까지 2주 일정을 새로 넣어요.');
});

test('anchorLabel / undoUntilLabel: 월 경계', () => {
	assert.equal(v.anchorLabel('2026-10-12'), '10/12(월)');
	assert.equal(v.undoUntilLabel('2026-10-12'), '10/11(일)');
	assert.equal(v.undoUntilLabel('2026-11-02'), '11/01(일)');
	assert.equal(v.undoUntilLabel('2026-12-01'), '11/30(월)');
});

test('canUndo: 시작 전만', () => {
	assert.equal(v.canUndo('2026-10-12', '2026-10-11'), true);
	assert.equal(v.canUndo('2026-10-12', '2026-10-12'), false);
});

test('parseTargetTime', () => {
	assert.equal(v.parseTargetTime('3:45:00'), 13500);
	assert.equal(v.parseTargetTime('45:30'), 2730);
	assert.equal(v.parseTargetTime(' '), null);
	assert.equal(v.parseTargetTime('abc'), 'invalid');
	assert.equal(v.parseTargetTime('1:99:00'), 'invalid');
	assert.equal(v.parseTargetTime('0:00'), 'invalid');
});

test('parseReplanInputs: 빈 값·오류·경고', () => {
	assert.deepEqual(v.parseReplanInputs({ weekly: '', long: '', target: '' }), { params: {}, errors: {}, warnings: [] });
	const r = v.parseReplanInputs({ weekly: '30', long: '35', target: '3:30:00' });
	assert.deepEqual(r.params, { recent_weekly_km: 30, recent_long_km: 35, target_time_sec: 12600 });
	assert.equal(r.warnings.length, 1);
	const e = v.parseReplanInputs({ weekly: '0', long: '-1', target: 'x' });
	assert.deepEqual(Object.keys(e.errors), ['weekly', 'long', 'target']);
	assert.equal(v.parseReplanInputs({ weekly: '250', long: '', target: '' }).warnings.length, 1);
});

test('replanQuery: 빈 값 제외', () => {
	assert.equal(v.replanQuery({}), '');
	assert.equal(v.replanQuery({ recent_weekly_km: 30, target_time_sec: 100 }), 'recent_weekly_km=30&target_time_sec=100');
});

test('canApply', () => {
	const p = P([], []);
	assert.equal(v.canApply({ preview: p, dirty: false, busy: false, hasError: false }), true);
	assert.equal(v.canApply({ preview: null, dirty: false, busy: false, hasError: false }), false);
	assert.equal(v.canApply({ preview: p, dirty: true, busy: false, hasError: false }), false);
	assert.equal(v.canApply({ preview: p, dirty: false, busy: true, hasError: false }), false);
	assert.equal(v.canApply({ preview: p, dirty: false, busy: false, hasError: true }), false);
});

test('notices: 0건 null, 3건 초과 외 k개', () => {
	assert.equal(v.externalNotice([]), null);
	assert.equal(v.preservedNotice([]), null);
	assert.equal(v.skippedNotice([]), null);
	const ext = ['2026-10-14', '2026-10-15', '2026-10-16', '2026-10-17', '2026-10-18'].map((date, id) => ({ id, date }));
	assert.match(v.externalNotice(ext), /5개\(10\/14, 10\/15, 10\/16 외 2개\)/);
	assert.match(v.preservedNotice(ext.slice(0, 1)), /1개는 그대로 둬요\(10\/14\)/);
	assert.match(v.skippedNotice(['2026-10-14']), /^10\/14에는/);
});

test('replanErrorView: 표의 행들', () => {
	const e = (status, code, phase) => v.replanErrorView({ status, code }, phase);
	assert.equal(e(404, 'NO_GOAL', 'preview').action, 'newGoal');
	assert.equal(e(404, 'NO_GOAL', 'undo').action, 'plan');
	assert.equal(e(409, 'RACE_WEEK', 'apply').action, 'back');
	assert.equal(e(409, 'CONFLICT', 'apply').action, 'repreview');
	assert.equal(e(409, 'REPLAN_LOCKED', 'undo').action, 'repreview');
	assert.equal(e(400, 'BAD_REQUEST', 'preview').action, null);
	assert.equal(e(503, 'X', 'preview').action, 'retry');
	assert.equal(v.replanErrorView(null, 'preview').action, 'retry');
	assert.equal(v.replanErrorView(null, 'apply').action, 'plan');
	assert.equal(v.replanErrorView(null, 'undo').action, 'plan');
});

test('startState 경계: 12km 이상 A, 0 초과 B, 공백 C, 기록 없음 D', () => {
	assert.equal(v.startState({ km4: 12, avg16: 0 }), 'A');
	assert.equal(v.startState({ km4: 11.9, avg16: 30 }), 'B');
	assert.equal(v.startState({ km4: 0, avg16: 20 }), 'C');
	assert.equal(v.startState({ km4: 0, avg16: 0 }), 'D');
});

test('inputFields: A·B 숨김, C 접힘, D 펼침', () => {
	assert.deepEqual(v.inputFields('A'), { weekly: false, long: false, open: false });
	assert.deepEqual(v.inputFields('B'), { weekly: false, long: false, open: false });
	assert.equal(v.inputFields('C').weekly, true);
	assert.equal(v.inputFields('C').open, false);
	assert.equal(v.inputFields('D').open, true);
});

test('startCardText·startSourceText: 출처별 문구', () => {
	const mk = (start_source, start_km, km4) => ({ start_source, start_km, basis: { km4, avg16: 0, long6: 0, long12: 0 } });
	assert.equal(v.startCardText(mk('history', 30, 30)), '첫 주 30km — 최근 4주 평균 30km 그대로');
	assert.match(v.startCardText(mk('floor', 12, 8)), /8km로 적어서 12km부터/);
	assert.match(v.startCardText(mk('user', 25, 0)), /입력한 값/);
	assert.match(v.startCardText(mk('avg16', 24, 0)), /16주 평균의 60%/);
	assert.match(v.startCardText(mk('default', 20, 0)), /기본값/);
	assert.equal(v.startSourceText(mk('history', 30.4, 30)), '시작 주간 30km · 최근 4주 기록 기준');
});

test('targetChangeText·fmtTarget', () => {
	assert.equal(v.fmtTarget(13500), '3:45:00');
	assert.equal(v.fmtTarget(2730), '45:30');
	assert.equal(v.targetChangeText(13500, 13800), '목표 3:45:00 → 3:50:00 기준으로 다시 짜요.');
	assert.equal(v.targetChangeText(13500, 13500), null);
	assert.equal(v.targetChangeText(13500, null), null);
});

test('longRunLine: 전후 비교·동일·없음', () => {
	const L = (s, k, l) => ({ week_start: s, planned_km: k, long_km: l });
	assert.equal(v.longRunLine(P([L('2026-10-12', 50, 32)], [L('2026-10-12', 36, 20), L('2026-11-16', 40, 28)])), '가장 긴 롱런 32 → 28km (11/16 주)');
	assert.equal(v.longRunLine(P([], [L('2026-10-12', 36, 20)])), '가장 긴 롱런 20km (10/12 주)');
	assert.equal(v.longRunLine(P([L('2026-10-12', 30, 20)], [L('2026-10-12', 30, 20)])), '가장 긴 롱런 20km (10/12 주)');
	assert.equal(v.longRunLine(P([], [W('2026-10-12', 30)])), null);
});
