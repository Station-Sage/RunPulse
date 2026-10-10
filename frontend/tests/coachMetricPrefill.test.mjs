import test from 'node:test';
import assert from 'node:assert/strict';
import { parseMetricPrefill, metricCoachHref, metricContextRef, metricQuestions } from '../src/lib/coachMetricPrefill.ts';

test('parseMetricPrefill: 유효한 slug·date만', () => {
	assert.deepEqual(parseMetricPrefill(new URLSearchParams('metric=tsb&date=2026-10-01')), { slug: 'tsb', date: '2026-10-01' });
	assert.equal(parseMetricPrefill(new URLSearchParams('metric=tsb')), null);
	assert.equal(parseMetricPrefill(new URLSearchParams('metric=a%20b&date=2026-10-01')), null);
	assert.equal(parseMetricPrefill(new URLSearchParams('metric=tsb&date=10-01')), null);
});

test('링크·ref·질문', () => {
	assert.equal(metricCoachHref('/v2', 'tsb', '2026-10-01'), '/v2/coach/new?metric=tsb&date=2026-10-01');
	assert.equal(metricContextRef({ slug: 'tsb', date: '2026-10-01' }), 'tsb@2026-10-01');
	const q = metricQuestions('TSB', '-8.3', '2026-10-01');
	assert.equal(q.length, 3);
	assert.ok(q[0].includes('10월 1일') && q[0].includes('-8.3'));
});
