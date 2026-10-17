import test from 'node:test';
import assert from 'node:assert/strict';
import { chipOf, dDayLabel, goalLine, kmLabel } from '../src/lib/raceCalendarView.ts';

const race = (o = {}) => ({ status: 'planned', adapt_choice: 'unasked', plan_state: 'none', ...o });

test('dDayLabel', () => {
	assert.equal(dDayLabel('2026-11-01', '2026-10-17'), 'D-15');
	assert.equal(dDayLabel('2026-10-17', '2026-10-17'), 'D-DAY');
	assert.equal(dDayLabel('2026-10-10', '2026-10-17'), 'D+7');
});

test('chipOf', () => {
	assert.equal(chipOf(race({ status: 'cancelled' }), false), '취소됨');
	assert.equal(chipOf(race({ status: 'done' }), false), '결과 연결');
	assert.equal(chipOf(race(), true), '목표 대회');
	assert.equal(chipOf(race({ adapt_choice: 'adapt', plan_state: 'applied' }), false), '반영됨');
	assert.equal(chipOf(race({ adapt_choice: 'adapt', plan_state: 'stale' }), false), '변경 후 미반영');
	assert.equal(chipOf(race({ adapt_choice: 'no_adapt' }), false), '조정 안 함');
	assert.equal(chipOf(race({ adapt_choice: 'later' }), false), '나중에');
	assert.equal(chipOf(race(), false), '질문 대기');
});

test('kmLabel and goalLine', () => {
	assert.equal(kmLabel(10), '10km');
	assert.equal(kmLabel(21.1), '21.1km');
	assert.equal(kmLabel(42.195), '42.195km');
	assert.equal(goalLine({ goal_type: null }), '');
	assert.equal(goalLine({ goal_type: 'finish' }), '완주');
	assert.equal(goalLine({ goal_type: 'time', goal_value: 3 * 3600 + 59 * 60 + 5 }), '3:59:05');
	assert.equal(goalLine({ goal_type: 'time', goal_value: 49 * 60 }), '49:00');
});
