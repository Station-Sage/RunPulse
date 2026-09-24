import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ringFraction, ringDash } from '../src/lib/scoreRing.ts';

test('ringFraction: 기본 0~100, clamp, null', () => {
	assert.equal(ringFraction(50), 0.5);
	assert.equal(ringFraction(150), 1);
	assert.equal(ringFraction(-5), 0);
	assert.equal(ringFraction(null), 0);
	assert.equal(ringFraction(NaN), 0);
});

test('ringFraction: 양방향 범위(TSB -40~40)', () => {
	assert.equal(ringFraction(0, -40, 40), 0.5);
	assert.equal(ringFraction(-40, -40, 40), 0);
	assert.equal(ringFraction(2.6, -40, 40), (2.6 + 40) / 80);
	assert.equal(ringFraction(1, 5, 5), 0);
});

test('ringDash: 둘레를 채움/나머지로 분할', () => {
	const circ = 2 * Math.PI * 10;
	const [fill, rest] = ringDash(0.25, 10).split(' ').map(Number);
	assert.ok(Math.abs(fill - circ * 0.25) < 0.01);
	assert.ok(Math.abs(fill + rest - circ) < 0.02);
	assert.equal(ringDash(2, 10).split(' ')[1], '0.00');
});
