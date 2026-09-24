import { test } from 'node:test';
import assert from 'node:assert/strict';
import { gapVerdict, countdownLabel, distanceLabel } from '../src/lib/raceHub.ts';

test('gapVerdict: null은 unknown, 60초 미만은 on', () => {
	assert.equal(gapVerdict(null).tone, 'unknown');
	assert.equal(gapVerdict(30).tone, 'on');
	assert.equal(gapVerdict(-59).tone, 'on');
});

test('gapVerdict: 느림/빠름 문구', () => {
	const slow = gapVerdict(252);
	assert.equal(slow.tone, 'behind');
	assert.equal(slow.label, '목표보다 4분 12초 느림');
	const fast = gapVerdict(-3700);
	assert.equal(fast.tone, 'ahead');
	assert.equal(fast.label, '목표보다 1시간 1분 빠름');
});

test('countdownLabel: D-day 경계', () => {
	assert.equal(countdownLabel(31), 'D-31');
	assert.equal(countdownLabel(0), 'D-DAY');
	assert.equal(countdownLabel(-3), 'D+3');
});

test('distanceLabel: 표준 거리 근사와 그 외', () => {
	assert.equal(distanceLabel(42.195), '풀 마라톤');
	assert.equal(distanceLabel(21.1), '하프');
	assert.equal(distanceLabel(10), '10K');
	assert.equal(distanceLabel(5), '5K');
	assert.equal(distanceLabel(15), '15.0km');
});
