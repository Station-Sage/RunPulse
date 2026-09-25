import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { medianPace, activityFlag } from '../src/lib/activityFlags.ts';

describe('medianPace', () => {
	it('returns median of 6 running paces', () => {
		const items = [340, 345, 350, 355, 360, 365].map((p) => ({
			activity_type: 'running',
			distance_m: 5000,
			avg_hr: 140,
			avg_pace_sec_km: p,
			route: [[1, 1], [2, 2]]
		}));
		assert.equal(medianPace(items), 352.5);
	});

	it('returns null for fewer than 5 runs', () => {
		const items = [340, 345, 350, 355].map((p) => ({
			activity_type: 'running',
			distance_m: 5000,
			avg_hr: 140,
			avg_pace_sec_km: p,
			route: [[1, 1], [2, 2]]
		}));
		assert.equal(medianPace(items), null);
	});
});

describe('activityFlag', () => {
	const median = 352.5;

	it('slow_pace: 677 sec/km over 3km is flagged', () => {
		const a = {
			activity_type: 'running',
			distance_m: 12000,
			avg_hr: 135,
			avg_pace_sec_km: 677,
			route: [[1, 1], [2, 2]]
		};
		// 677 > 352.5 * 1.5 = 528.75
		assert.equal(activityFlag(a, median)?.key, 'slow_pace');
	});

	it('slow_pace not triggered for distance < 3000m', () => {
		const a = {
			activity_type: 'running',
			distance_m: 2000,
			avg_hr: 135,
			avg_pace_sec_km: 677,
			route: [[1, 1], [2, 2]]
		};
		// Next rule: hr present, route present → null
		assert.equal(activityFlag(a, median), null);
	});

	it('no_hr: null avg_hr returns no_hr flag', () => {
		const a = {
			activity_type: 'running',
			distance_m: 5000,
			avg_hr: null,
			avg_pace_sec_km: 350,
			route: [[1, 1], [2, 2]]
		};
		assert.equal(activityFlag(a, median)?.key, 'no_hr');
	});

	it('no_gps: hr present but no route returns no_gps flag', () => {
		const a = {
			activity_type: 'running',
			distance_m: 5000,
			avg_hr: 140,
			avg_pace_sec_km: 350,
			route: null
		};
		assert.equal(activityFlag(a, median)?.key, 'no_gps');
	});

	it('treadmill_running returns null', () => {
		const a = {
			activity_type: 'treadmill_running',
			distance_m: 5000,
			avg_hr: null,
			avg_pace_sec_km: 677,
			route: null
		};
		assert.equal(activityFlag(a, median), null);
	});

	it('swimming returns null', () => {
		const a = {
			activity_type: 'swimming',
			distance_m: 1000,
			avg_hr: null,
			avg_pace_sec_km: 120,
			route: null
		};
		assert.equal(activityFlag(a, median), null);
	});

	it('normal running row returns null', () => {
		const a = {
			activity_type: 'running',
			distance_m: 10000,
			avg_hr: 155,
			avg_pace_sec_km: 330,
			route: [[1, 1], [2, 2]]
		};
		assert.equal(activityFlag(a, median), null);
	});
});
