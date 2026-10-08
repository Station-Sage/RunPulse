import { test } from 'node:test';
import assert from 'node:assert/strict';
import { expiryText, formatBytes, rangeBody } from '../src/lib/exports.ts';

const item = (over = {}) => ({
	id: 'a', state: 'done', created_at: null, finished_at: null, error: null,
	result: { filename: 'a.zip', size_bytes: 1, expires_at: '2026-10-10T00:00:00', row_counts: {} }, ...over
});

test('formatBytes: 단위 전환', () => {
	assert.equal(formatBytes(500), '500B');
	assert.equal(formatBytes(2048), '2KB');
	assert.equal(formatBytes(3 * 1024 * 1024), '3.0MB');
});

test('expiryText: 남은 일수와 만료', () => {
	assert.equal(expiryText(item(), new Date('2026-10-07T00:00:00')), '3일 안에 받을 수 있어요');
	assert.equal(expiryText(item(), new Date('2026-10-09T12:00:00')), '오늘까지 받을 수 있어요');
	assert.equal(expiryText(item({ state: 'expired' })), '보관 기간이 지났어요');
});

test('rangeBody: 빈 값은 생략', () => {
	assert.deepEqual(rangeBody('', ''), {});
	assert.deepEqual(rangeBody('2026-01-01', ''), { from: '2026-01-01' });
});
