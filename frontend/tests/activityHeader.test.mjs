import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { backTarget, mergedSourceLabel } from '../src/lib/activityHeader.ts';

describe('mergedSourceLabel', () => {
	it('단일 소스', () => {
		assert.equal(mergedSourceLabel('garmin', []), 'Garmin');
		assert.equal(mergedSourceLabel('strava', undefined), 'Strava');
	});
	it('대표 소스가 앞에 ★', () => {
		const s = [
			{ id: 2, provider: 'intervals', is_canonical: false },
			{ id: 1, provider: 'garmin', is_canonical: true }
		];
		assert.equal(mergedSourceLabel('garmin', s), 'Garmin ★ · Intervals');
	});
});

describe('backTarget', () => {
	it('알려진 출처', () => {
		assert.equal(backTarget('today').label, '오늘');
	});
	it('모르면 활동 목록', () => {
		assert.equal(backTarget('zzz').path, '/library/activities');
		assert.equal(backTarget(null).path, '/library/activities');
	});
	it('metric → 메트릭 목록', () => {
		assert.equal(backTarget('metric').path, '/library/metrics');
	});
});
