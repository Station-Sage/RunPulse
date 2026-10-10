import test from 'node:test';
import assert from 'node:assert/strict';
import { clampStep, nextStep, prevStep, isLast, shouldRedirect, rangeFor, etaLabel, startStep } from '../src/lib/onboarding.ts';

test('step transitions clamp', () => {
	assert.equal(nextStep(0), 1);
	assert.equal(nextStep(4), 4);
	assert.equal(prevStep(0), 0);
	assert.equal(prevStep(3), 2);
	assert.equal(clampStep('x'), 0);
	assert.equal(clampStep(9), 0);
	assert.ok(isLast(4) && !isLast(2));
});

test('redirect only for empty pending accounts', () => {
	const empty = { connected_count: 0, activity_count: 0 };
	assert.ok(shouldRedirect(empty, 'pending'));
	assert.ok(!shouldRedirect(empty, 'skipped'));
	assert.ok(!shouldRedirect(empty, 'done'));
	assert.ok(!shouldRedirect({ connected_count: 1, activity_count: 0 }, 'pending'));
	assert.ok(!shouldRedirect({ connected_count: 0, activity_count: 3 }, 'pending'));
	assert.ok(!shouldRedirect(null, 'pending'));
});

test('rangeFor and eta', () => {
	const t = new Date('2026-10-10T00:00:00Z');
	assert.deepEqual(rangeFor('90d', t), { from: '2026-07-12', to: '2026-10-10' });
	assert.equal(rangeFor('1y', t).from, '2025-10-10');
	assert.equal(etaLabel('최근 90일', 60), '최근 90일 · 약 3분');
	assert.equal(etaLabel('최근 90일', null), '최근 90일');
});

test('query step wins over saved (OAuth return)', () => {
	assert.equal(startStep('2', 1), 2);
	assert.equal(startStep(null, 3), 3);
});
