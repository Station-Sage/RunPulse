import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { isValidDate, dateLabel, shiftDate, fmtDur, stageSegments, baselineNote } from '../src/lib/wellnessDay.ts';

describe('wellnessDay', () => {
	it('isValidDate rejects bad formats and impossible dates', () => {
		assert.equal(isValidDate('2026-10-04'), true);
		assert.equal(isValidDate('2026-13-01'), false);
		assert.equal(isValidDate('2026-02-30'), false);
		assert.equal(isValidDate('abc'), false);
	});
	it('dateLabel formats Korean with weekday', () => {
		assert.equal(dateLabel('2026-10-04'), '10월 4일 (일)');
	});
	it('shiftDate crosses month boundary', () => {
		assert.equal(shiftDate('2026-10-01', -1), '2026-09-30');
		assert.equal(shiftDate('2026-12-31', 1), '2027-01-01');
	});
	it('fmtDur handles null and minutes-only', () => {
		assert.equal(fmtDur(null), '—');
		assert.equal(fmtDur(2700), '45m');
		assert.equal(fmtDur(26000), '7h 13m');
	});
	it('stageSegments returns percentages summing to 100, empty on null', () => {
		assert.deepEqual(stageSegments(null), []);
		assert.deepEqual(stageSegments({ deep: null, light: null, rem: null, awake: null }), []);
		const segs = stageSegments({ deep: 3600, light: 14400, rem: 3600, awake: 0 });
		assert.equal(segs.length, 3);
		assert.equal(Math.round(segs.reduce((a, s) => a + s.pct, 0)), 100);
	});
	it('baselineNote shows progress under 7', () => {
		assert.equal(baselineNote(3), '기준선 수집 중 (3/7일)');
		assert.equal(baselineNote(7), null);
		assert.equal(baselineNote(undefined), null);
	});
});
