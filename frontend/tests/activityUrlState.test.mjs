import test from 'node:test';
import assert from 'node:assert/strict';
import { parseSeg } from '../src/lib/activityUrlState.ts';

test('parseSeg: 양의 정수만 받는다', () => {
	assert.equal(parseSeg('3'), 3);
	assert.equal(parseSeg('0'), null);
	assert.equal(parseSeg('-1'), null);
	assert.equal(parseSeg('abc'), null);
	assert.equal(parseSeg(null), null);
});
