import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
	normalizeDateParams,
	validatePageParam,
	validateSortParam,
	validateActivityId,
	isValidMetricSlug,
	normalizeRangeParams
} from '../src/lib/utils/validation.ts';

test('normalizeDateParams', async (t) => {
	await t.test('should return current date when params are undefined', () => {
		const today = new Date();
		const result = normalizeDateParams();
		assert.strictEqual(result.year, today.getFullYear());
		assert.strictEqual(result.month, today.getMonth() + 1);
	});

	await t.test('should accept valid year and month', () => {
		const result = normalizeDateParams(2026, 10);
		assert.strictEqual(result.year, 2026);
		assert.strictEqual(result.month, 10);
	});

	await t.test('should normalize invalid month to current month', () => {
		const today = new Date();
		const result = normalizeDateParams(2026, 13);
		assert.strictEqual(result.year, 2026);
		assert.strictEqual(result.month, today.getMonth() + 1);
	});
});

test('validatePageParam', async (t) => {
	await t.test('should return 1 for undefined', () => {
		assert.strictEqual(validatePageParam(), 1);
	});

	await t.test('should return valid page number', () => {
		assert.strictEqual(validatePageParam(3, 10), 3);
		assert.strictEqual(validatePageParam('5', 10), 5);
	});

	await t.test('should cap page to maxPages', () => {
		assert.strictEqual(validatePageParam(10, 5), 5);
	});

	await t.test('should return 1 for invalid', () => {
		assert.strictEqual(validatePageParam(-1), 1);
		assert.strictEqual(validatePageParam('abc'), 1);
	});
});

test('validateActivityId', async (t) => {
	await t.test('should return undefined for invalid input', () => {
		assert.strictEqual(validateActivityId(), undefined);
		assert.strictEqual(validateActivityId('abc'), undefined);
	});

	await t.test('should return parsed id for valid input', () => {
		assert.strictEqual(validateActivityId(123), 123);
		assert.strictEqual(validateActivityId('456'), 456);
	});
});

test('isValidMetricSlug', async (t) => {
	await t.test('should validate metric slugs', () => {
		assert.strictEqual(isValidMetricSlug('utrs'), true);
		assert.strictEqual(isValidMetricSlug('ctl_value'), true);
		assert.strictEqual(isValidMetricSlug('race-pred'), false);
	});
});

test('normalizeRangeParams', async (t) => {
	await t.test('should accept valid ISO dates', () => {
		const result = normalizeRangeParams('2026-10-01', '2026-10-31');
		assert.strictEqual(result.from, '2026-10-01');
		assert.strictEqual(result.to, '2026-10-31');
	});

	await t.test('should return empty object for no params', () => {
		const result = normalizeRangeParams();
		assert.strictEqual(result.from, undefined);
		assert.strictEqual(result.to, undefined);
	});

	await t.test('should ignore invalid dates', () => {
		const result = normalizeRangeParams('invalid', '2026-10-31');
		assert.strictEqual(result.from, undefined);
		assert.strictEqual(result.to, '2026-10-31');
	});
});

test('normalizeMonthParam: 잘못된 형식·미래 달은 이번 달, 정상 값은 유지', async () => {
	const { normalizeMonthParam } = await import('../src/lib/utils/validation.ts');
	const now = new Date(2026, 10, 9); // 2026-11
	assert.deepEqual(normalizeMonthParam('2026-10', now), { year: 2026, month: 10, ym: '2026-10' });
	assert.equal(normalizeMonthParam('2099-99', now).ym, '2026-11');
	assert.equal(normalizeMonthParam('2026-12', now).ym, '2026-11');
	assert.equal(normalizeMonthParam('abc', now).ym, '2026-11');
	assert.equal(normalizeMonthParam('2026-11', now).ym, '2026-11');
});
