import test from 'node:test';
import assert from 'node:assert/strict';
import { gpxUrl } from '../src/lib/activityExport.ts';

test('gpxUrl points at the export endpoint', () => {
	assert.equal(gpxUrl(42), '/api/v1/library/activities/42/export.gpx');
});
