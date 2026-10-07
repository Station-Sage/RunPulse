import { test } from 'node:test';
import assert from 'node:assert/strict';
import { formatProfileValue, parseProfileInput, usedValue } from '../src/lib/profileRows.ts';

test('formatProfileValue: 단위별 포맷', () => {
	assert.equal(formatProfileValue('hrmax', 188), '188bpm');
	assert.equal(formatProfileValue('threshold_pace', 305), '5:05/km');
	assert.equal(formatProfileValue('weekly_km', 45), '45km');
	assert.equal(formatProfileValue('lthr', null), '—');
});

test('parseProfileInput: 빈 값 null, m:ss 파싱, 잘못된 값 undefined', () => {
	assert.equal(parseProfileInput('hrmax', ' '), null);
	assert.equal(parseProfileInput('threshold_pace', '5:05'), 305);
	assert.equal(parseProfileInput('threshold_pace', '5:75'), undefined);
	assert.equal(parseProfileInput('hrmax', 'abc'), undefined);
	assert.equal(parseProfileInput('hrmax', '190'), 190);
});

test('usedValue: using 기준 값', () => {
	const row = { key: 'hrmax', self: { value: 188 }, device: { value: 190 }, manual: null, using: 'device' };
	assert.equal(usedValue(row), 190);
	assert.equal(usedValue({ ...row, using: 'none' }), null);
});
