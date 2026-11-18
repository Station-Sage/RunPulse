import test from 'node:test';
import assert from 'node:assert/strict';
import { softLoad } from '../src/lib/loadTimeout.ts';

test('softLoad: 정상 값 통과', async () => {
	assert.equal(await softLoad(Promise.resolve(5), 100), 5);
});
test('softLoad: 거절은 null', async () => {
	assert.equal(await softLoad(Promise.reject(new Error('x')), 100), null);
});
test('softLoad: 시간 초과는 null', async () => {
	assert.equal(await softLoad(new Promise(() => {}), 30), null);
});
