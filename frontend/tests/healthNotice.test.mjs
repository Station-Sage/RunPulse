import { test } from 'node:test';
import assert from 'node:assert/strict';
import { loadCoverageNotice } from '../src/lib/healthNotice.ts';

const H = (runs, missing) => ({ window_days: 90, runs, missing, missing_ratio: runs ? missing / runs : 0 });

test('누락이 적거나 비율이 낮으면 알림 없음', () => {
	assert.equal(loadCoverageNotice(null), null);
	assert.equal(loadCoverageNotice(H(50, 2)), null); // 3건 미만
	assert.equal(loadCoverageNotice(H(50, 5)), null); // 10% < 20%
});

test('누락 3건 이상·20% 이상이면 문구', () => {
	const msg = loadCoverageNotice(H(45, 36));
	assert.match(msg, /45회 중 36회/);
	assert.match(msg, /동기화/);
});
