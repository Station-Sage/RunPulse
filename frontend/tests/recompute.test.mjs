import { test } from 'node:test';
import assert from 'node:assert/strict';
import { formatDelta, formatMetric, progressPct } from '../src/lib/recompute.ts';

test('formatMetric: 마라톤은 h:mm:ss, 나머지는 소수 1자리', () => {
	assert.equal(formatMetric('marathon', 12345), '3:25:45');
	assert.equal(formatMetric('ctl', 42.46), '42.5');
	assert.equal(formatMetric('vdot', null), '—');
});

test('formatDelta: 상태별 문구', () => {
	const base = { slug: 'ctl', label: 'CTL', unit: '', before: 40, after: 42.5 };
	assert.equal(formatDelta({ ...base, delta: 2.5, status: 'changed' }), '+2.5');
	assert.equal(formatDelta({ ...base, delta: -1, status: 'changed' }), '−1');
	assert.equal(formatDelta({ ...base, delta: 0, status: 'unchanged' }), '변화 없음');
	assert.equal(formatDelta({ ...base, delta: null, status: 'unavailable' }), '데이터 부족');
	assert.equal(formatDelta({ ...base, slug: 'marathon', delta: -95, status: 'changed' }), '−95초');
});

test('progressPct', () => {
	assert.equal(progressPct({ progress: { done: 30, total: 90 } }), 33);
	assert.equal(progressPct({ progress: { done: 0, total: 0 } }), 0);
});
