import test from 'node:test';
import assert from 'node:assert/strict';
import { validateRange, estimateView } from '../src/lib/rangeSync.ts';

test('validateRange', () => {
	assert.equal(validateRange('', '2026-01-02', '2026-10-01'), '시작일과 종료일을 고르세요');
	assert.match(validateRange('2026-02-01', '2026-01-01', '2026-10-01'), /늦어요/);
	assert.match(validateRange('2026-01-01', '2026-12-01', '2026-10-01'), /오늘/);
	assert.equal(validateRange('2026-01-01', '2026-01-31', '2026-10-01'), null);
});

test('estimateView', () => {
	const base = { provider: 'garmin', days: 30, batches: 3, requests: 33,
		rate_limit: { window_15m_left: 50, daily_left: 500 }, allowed: true, message_ko: null };
	const ok = estimateView(base);
	assert.equal(ok.canStart, true);
	assert.match(ok.lines[0], /33회/);
	const no = estimateView({ ...base, allowed: false, message_ko: '최대 90일' });
	assert.equal(no.canStart, false);
	assert.ok(no.lines.includes('최대 90일'));
	assert.ok(estimateView({ ...base, rate_limit: { window_15m_left: 5, daily_left: 10 } }).lines.some((l) => l.includes('멈출')));
});
