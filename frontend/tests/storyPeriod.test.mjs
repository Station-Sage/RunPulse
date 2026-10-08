import test from 'node:test';
import assert from 'node:assert/strict';
import { isoWeekId, storyScope } from '../src/lib/storyPeriod.ts';

test('storyScope: id 형태로 단위 판별', () => {
	assert.equal(storyScope('2026-10'), 'month');
	assert.equal(storyScope('2026-W41'), 'week');
	assert.equal(storyScope('b-3-build'), 'block');
});

test('isoWeekId: 연말·연초 경계', () => {
	assert.equal(isoWeekId('2026-10-08'), '2026-W41');
	assert.equal(isoWeekId('2026-01-01'), '2026-W01');
	assert.equal(isoWeekId('2027-01-01'), '2026-W53');
	assert.equal(isoWeekId('2024-12-30'), '2025-W01');
});
