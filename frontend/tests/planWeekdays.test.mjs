import test from 'node:test';
import assert from 'node:assert/strict';
import { parseRunWeekdays, toggleWeekday, needsInjuryNotice } from '../src/lib/planPrefill.ts';

test('parseRunWeekdays: 유효값만, 정렬·중복 제거', () => {
	assert.deepEqual(parseRunWeekdays('4,0,2,2'), [0, 2, 4]);
	assert.deepEqual(parseRunWeekdays('7,-1,x,,3'), [3]);
	assert.deepEqual(parseRunWeekdays(null), []);
});

test('toggleWeekday', () => {
	assert.deepEqual(toggleWeekday([1, 3], 2), [1, 2, 3]);
	assert.deepEqual(toggleWeekday([1, 3], 1), [3]);
});

test('needsInjuryNotice: 6일 이상', () => {
	assert.equal(needsInjuryNotice([0, 1, 2, 3, 4]), false);
	assert.equal(needsInjuryNotice([0, 1, 2, 3, 4, 5]), true);
	assert.equal(needsInjuryNotice([0, 1, 2, 3, 4, 5, 6]), true);
});
