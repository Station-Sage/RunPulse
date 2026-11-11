// V2-AUDIT 묶음 E(plan/coach/onboarding) 프런트 헬퍼.
import test from 'node:test';
import assert from 'node:assert/strict';
import { acwrRangeText, ctlBar, noteAction, planStepText, targetLine } from '../src/lib/planDetailView.ts';
import { metricPrefillError, metricPrefillState, metricQuestions } from '../src/lib/coachMetricPrefill.ts';
import { lastTalkLabel, parseThreadId } from '../src/lib/threadAge.ts';
import { stepHref, welcomeGuardApplies } from '../src/lib/onboarding.ts';
import { checkProfileInput } from '../src/lib/profileRows.ts';
import { reasonText } from '../src/lib/coachEngine.ts';

test('P-10 acwrRangeText: 서버 범위만, 없으면 null', () => {
	assert.equal(acwrRangeText([0.8, 1.3]), '적정 0.8~1.3');
	assert.equal(acwrRangeText(undefined), null);
	assert.equal(acwrRangeText([NaN, 1]), null);
});

test('P-10 ctlBar: 최근 1년 최고 대비', () => {
	assert.deepEqual(ctlBar(40, { max: 80, label: '최근 1년 최고' }), { pct: 50, caption: '최근 1년 최고 80 대비 50%' });
	assert.equal(ctlBar(40, null), null);
	assert.equal(ctlBar(null, { max: 80, label: 'x' }), null);
	assert.equal(ctlBar(120, { max: 80, label: 'x' }).pct, 100);
});

test('P-16 noteAction: 변경 없음 null, 비우면 clear', () => {
	assert.equal(noteAction('a', 'a'), null);
	assert.equal(noteAction('  ', 'a'), 'clear');
	assert.equal(noteAction('b', 'a'), 'save');
	assert.equal(noteAction('', ''), null);
});

test('P-14 planStepText / P-20 targetLine', () => {
	assert.equal(planStepText(1), '단계 1/2');
	assert.equal(planStepText(2), '단계 2/2');
	assert.deepEqual(targetLine('3:45:00'), { text: '목표 기록 3:45:00', action: '바꾸기' });
	assert.equal(targetLine(null).action, '목표 기록 정하기');
	assert.ok(!targetLine(null).text.includes('없음 바꾸기'));
});

test('C-07 metricQuestions: 미해결 조사 표기 없음', () => {
	for (const q of metricQuestions('체력', '52', '2026-10-01')) assert.ok(!/\((은|는|이|가|을|를)\)/.test(q), q);
});

test('C-08 metricPrefillState: 소문자화·날짜 기본값·미래·형식', () => {
	const today = '2026-11-10';
	assert.equal(metricPrefillState(new URLSearchParams(''), today), null);
	assert.deepEqual(metricPrefillState(new URLSearchParams('metric=TSB'), today), { ok: true, prefill: { slug: 'tsb', date: today } });
	assert.equal(metricPrefillState(new URLSearchParams('metric=tsb&date=2026-11-11'), today).reason, 'future');
	assert.equal(metricPrefillState(new URLSearchParams('metric=tsb&date=11-01'), today).reason, 'bad_date');
	assert.equal(metricPrefillState(new URLSearchParams('metric=a%20b'), today).reason, 'bad_metric');
	assert.ok(!metricPrefillError('unknown_metric').includes('활동'));
});

test('C-09 parseThreadId: 숫자만', () => {
	assert.equal(parseThreadId('12'), 12);
	assert.equal(parseThreadId('12abc'), null);
	assert.equal(parseThreadId('0'), null);
	assert.equal(parseThreadId('-1'), null);
	assert.equal(parseThreadId(''), null);
});

test('C-15 lastTalkLabel / C-14 unexpected 사유', () => {
	assert.equal(lastTalkLabel('2주 전'), '마지막 대화 2주 전');
	assert.equal(lastTalkLabel(null), null);
	assert.equal(reasonText('unexpected'), '예기치 못한 오류');
});

test('E-25 stepHref / S-22 welcomeGuardApplies', () => {
	assert.equal(stepHref('/v2', 3), '/v2/welcome?step=3');
	assert.equal(stepHref('/v2', 9), '/v2/welcome?step=0');
	assert.equal(welcomeGuardApplies('/v2/library', '/v2'), true);
	assert.equal(welcomeGuardApplies('/v2/coach/12', '/v2'), true);
	assert.equal(welcomeGuardApplies('/v2/data/sources', '/v2'), false);
	assert.equal(welcomeGuardApplies('/v2/welcome', '/v2'), false);
	assert.equal(welcomeGuardApplies('/v2/libraryx', '/v2'), false);
});

test('S-19 checkProfileInput: 범위·형식 안내', () => {
	assert.deepEqual(checkProfileInput('hrmax', ''), { value: null, error: null });
	assert.equal(checkProfileInput('hrmax', '185').value, 185);
	assert.match(checkProfileInput('hrmax', '999').error, /120~230bpm/);
	assert.match(checkProfileInput('hrmax', 'abc').error, /숫자/);
	assert.equal(checkProfileInput('threshold_pace', '5:10').value, 310);
	assert.match(checkProfileInput('threshold_pace', '9999').error, /2:30\/km~10:00\/km/);
	assert.ok(checkProfileInput('hrmax', '-5').error);
});
