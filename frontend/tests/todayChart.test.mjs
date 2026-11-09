import { test } from 'node:test';
import assert from 'node:assert/strict';
import { emptyTrendData, shouldFetchChart } from '../src/lib/todayChart.ts';

test('shouldFetchChart — CTL 없으면 추세 요청 안 함 (T-25)', () => {
	assert.equal(shouldFetchChart({ status: { training_status: { ctl: null } } }), false);
	assert.equal(shouldFetchChart({ status: { training_status: { ctl: 42.1 } } }), true);
	assert.equal(shouldFetchChart({ status: { training_status: { ctl: 0 } } }), true);
});

test('emptyTrendData', () => {
	assert.deepEqual(emptyTrendData('tsb').points, []);
});
