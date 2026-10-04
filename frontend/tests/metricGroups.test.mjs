import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeCategory, cardLimit, limitCards } from '../src/lib/metricGroups.ts';

test('normalizeCategory maps legacy and unknown values', () => {
	assert.equal(normalizeCategory('readiness'), 'today');
	assert.equal(normalizeCategory('capacity'), 'ability');
	assert.equal(normalizeCategory('body'), 'vitals');
	assert.equal(normalizeCategory('load'), 'load');
	assert.equal(normalizeCategory('zzz'), 'all');
	assert.equal(normalizeCategory(null), 'all');
});

test('cardLimit is 2 for env/hr_ref else 4', () => {
	assert.equal(cardLimit('env'), 2);
	assert.equal(cardLimit('load'), 4);
});

test('limitCards truncates unless expanded', () => {
	const a = [1, 2, 3, 4, 5, 6];
	assert.deepEqual(limitCards(a, 'load', false), { shown: [1, 2, 3, 4], hidden: 2 });
	assert.deepEqual(limitCards(a, 'env', false), { shown: [1, 2], hidden: 4 });
	assert.deepEqual(limitCards(a, 'load', true), { shown: a, hidden: 0 });
	assert.deepEqual(limitCards([1], 'load', false), { shown: [1], hidden: 0 });
});
