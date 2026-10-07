import test from 'node:test';
import assert from 'node:assert/strict';
import { activeDataTab, formatBytes, runIsBad, runRange, runStatusLabel } from '../src/lib/dataArea.ts';

test('activeDataTab: 하위 경로는 상위 탭으로', () => {
	assert.equal(activeDataTab('/data'), '/data');
	assert.equal(activeDataTab('/data/sync/'), '/data/sync');
	assert.equal(activeDataTab('/data/sources/garmin'), '/data/sources');
	assert.equal(activeDataTab('/data/unknown'), '/data');
});

test('runStatusLabel·runIsBad', () => {
	assert.equal(runStatusLabel('completed'), '완료');
	assert.equal(runStatusLabel('x'), 'x');
	assert.equal(runIsBad('failed'), true);
	assert.equal(runIsBad('completed'), false);
});

test('formatBytes·runRange', () => {
	assert.equal(formatBytes(500), '500 B');
	assert.equal(formatBytes(2048), '2 KB');
	assert.equal(formatBytes(5 * 1024 * 1024), '5.0 MB');
	assert.equal(runRange('2026-10-01', '2026-10-07'), '10/01~10/07');
	assert.equal(runRange('2026-10-01', '2026-10-01'), '10/01');
	assert.equal(runRange(null, null), '');
});
