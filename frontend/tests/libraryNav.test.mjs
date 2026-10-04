import { test } from 'node:test';
import assert from 'node:assert/strict';
import { saveMetricsSearch, metricsBackHref, fromToday } from '../src/lib/libraryNav.ts';

const mem = () => {
	const m = new Map();
	return { setItem: (k, v) => m.set(k, v), removeItem: (k) => m.delete(k), getItem: (k) => m.get(k) ?? null };
};

test('저장된 필터가 있으면 그 URL로, 없으면 기본', () => {
	const s = mem();
	assert.equal(metricsBackHref('/v2', s), '/v2/library/metrics');
	saveMetricsSearch('?category=load&q=ac', s);
	assert.equal(metricsBackHref('/v2', s), '/v2/library/metrics?category=load&q=ac');
	saveMetricsSearch('', s);
	assert.equal(metricsBackHref('/v2', s), '/v2/library/metrics');
});

test('스토리지 없음/예외에도 안전', () => {
	assert.equal(metricsBackHref('/v2', { getItem: () => { throw new Error('x'); } }), '/v2/library/metrics');
});

test('fromToday', () => {
	assert.equal(fromToday('?from=today'), true);
	assert.equal(fromToday('?from=coach'), false);
	assert.equal(fromToday(''), false);
});
