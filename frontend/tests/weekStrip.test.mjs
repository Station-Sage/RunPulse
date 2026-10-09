import { test } from 'node:test';
import assert from 'node:assert/strict';
import { dayCell, dowOf, weekSummary, hasWeekPlan } from '../src/lib/weekStrip.ts';

const d = (o) => ({ date: '2026-09-28', state: 'upcoming', workout_type: 'easy', title: '이지런', planned_km: 8, session_id: 1, activity_id: null, substituted: false, today: false, ...o });

test('요일 계산', () => {
	assert.equal(dowOf('2026-09-28'), '월');
	assert.equal(dowOf('2026-10-04'), '일');
});

test('상태 기호: 이행·부족·놓침·예정', () => {
	assert.equal(dayCell(d({ state: 'done' })).symbol, '●');
	assert.equal(dayCell(d({ state: 'partial' })).symbol, '◐');
	assert.equal(dayCell(d({ state: 'skipped' })).tone, 'missed');
	assert.equal(dayCell(d({ state: 'missed' })).symbol, '○');
	assert.equal(dayCell(d({ state: 'upcoming' })).tone, 'upcoming');
});

test('오늘 예정은 ◉, 오늘 이미 이행했으면 ●', () => {
	assert.equal(dayCell(d({ today: true })).symbol, '◉');
	assert.equal(dayCell(d({ today: true, state: 'done' })).symbol, '●');
});

test('대체는 ●가 아니라 ⟳', () => {
	assert.equal(dayCell(d({ state: 'done', substituted: true })).symbol, '⟳');
});

test('휴식 ┄, 계획 전은 텍스트만·링크 없음', () => {
	assert.equal(dayCell(d({ state: 'rest', workout_type: null, title: null })).symbol, '┄');
	const p = dayCell(d({ state: 'pre_plan', workout_type: null, title: null }));
	assert.equal(p.label, '계획 전');
	assert.equal(p.linkable, false);
});

test('요약 문구', () => {
	assert.equal(weekSummary({ done_km: 12.5, plan_km: 40, key_done: 1, key_total: 2, days: [] }), '이번 주 12.5/40km · 핵심 1/2');
	assert.equal(weekSummary({ done_km: 0, plan_km: 20, key_done: 0, key_total: 0, days: [] }), '이번 주 0/20km');
});

test('계획 없으면 숨김', () => {
	assert.equal(hasWeekPlan(null), false);
	assert.equal(hasWeekPlan({ done_km: 0, plan_km: 0, key_done: 0, key_total: 0, days: [d({ state: 'rest', workout_type: null })] }), false);
	assert.equal(hasWeekPlan({ done_km: 0, plan_km: 8, key_done: 0, key_total: 0, days: [d({})] }), true);
});
