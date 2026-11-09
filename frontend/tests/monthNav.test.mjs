import { test } from 'node:test';
import assert from 'node:assert/strict';
import { closeAction, isAtMinMonth, monthSlice } from '../src/lib/monthNav.ts';

test('closeAction — 오늘에서 왔을 때만 뒤로 (T-23)', () => {
	assert.equal(closeAction('/v2/today', '/v2'), 'back');
	assert.equal(closeAction(null, '/v2'), 'today');
	assert.equal(closeAction('/v2/library', '/v2'), 'today');
});

test('isAtMinMonth (T-21)', () => {
	assert.equal(isAtMinMonth(2000, 1), true);
	assert.equal(isAtMinMonth(2000, 2), false);
});

test('monthSlice (T-24)', () => {
	const pts = [
		{ date: '2026-09-30', value: 1 },
		{ date: '2026-10-01', value: 2 },
		{ date: '2026-10-31', value: 3 },
		{ date: '2026-11-01', value: 4 }
	];
	assert.deepEqual(monthSlice(pts, 2026, 10, false).map((p) => p.value), [2, 3]);
	assert.deepEqual(monthSlice(pts, 2026, 11, true).map((p) => p.value), [1, 2, 3, 4]);
});
