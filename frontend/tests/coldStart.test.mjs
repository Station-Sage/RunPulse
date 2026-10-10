import test from 'node:test';
import assert from 'node:assert/strict';
import { coldStartSummary } from '../src/lib/coldStart.ts';

const act = (id, start, d, s) => ({ id, name: 'r', activity_type: 'running', start_time: start, distance_m: d, duration_sec: s, source: 'garmin' });

test('활동 없으면 null', () => {
	assert.equal(coldStartSummary([]), null);
	assert.equal(coldStartSummary(null), null);
});
test('한 건이면 첫 기록 문구', () => {
	const r = coldStartSummary([act(1, '2026-10-01T07:00:00', 5000, 1500)]);
	assert.equal(r.headline, '첫 기록이 들어왔어요');
	assert.equal(r.activityId, 1);
});
test('여러 건이면 가장 최근 활동', () => {
	const r = coldStartSummary([act(1, '2026-10-01T07:00:00', 5000, 1500), act(2, '2026-10-03T07:00:00', 8000, 2400)]);
	assert.equal(r.activityId, 2);
	assert.match(r.headline, /2건/);
});
