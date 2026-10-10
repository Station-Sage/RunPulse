import test from 'node:test';
import assert from 'node:assert/strict';
import { evidenceChips, threadBackHref } from '../src/lib/activityEvidence.ts';

test('evidenceChips: 값 있는 항목만', () => {
	assert.deepEqual(
		evidenceChips({ distance_km: 21.1, pace: '5:35/km', decoupling_pct: 6.84, tsb: -8.3 }),
		['21.1km', '페이스 5:35/km', '디커플링 6.8%', 'TSB -8.3']
	);
	assert.deepEqual(evidenceChips({ distance_km: 5, pace: null, decoupling_pct: null, tsb: 2 }), ['5.0km', 'TSB +2.0']);
	assert.deepEqual(evidenceChips({ distance_km: null, pace: null, decoupling_pct: null, tsb: null }), []);
});

test('threadBackHref: 활동 스레드는 활동으로', () => {
	assert.equal(threadBackHref({ kind: 'activity', ref: '12' }, '').href, '/library/12?from=coach');
	assert.equal(threadBackHref({ kind: 'activity', ref: 'x' }, '').href, '/coach');
	assert.equal(threadBackHref(null, '/b').href, '/b/coach');
});

test('threadBackHref: 지표 스레드는 지표 상세로', () => {
	assert.equal(threadBackHref({ kind: 'metric', ref: 'tsb@2026-10-01' }, '').href, '/library/metrics/tsb?date=2026-10-01');
	assert.equal(threadBackHref({ kind: 'metric', ref: 'bad' }, '').href, '/coach');
});
