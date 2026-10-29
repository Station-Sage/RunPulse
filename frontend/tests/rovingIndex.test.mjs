import test from 'node:test';
import assert from 'node:assert/strict';
import { nextIndex } from '../src/lib/a11y/rovingIndex.ts';

test('nextIndex: 화살표는 순환한다', () => {
	assert.equal(nextIndex(0, 'ArrowRight', 3), 1);
	assert.equal(nextIndex(2, 'ArrowRight', 3), 0);
	assert.equal(nextIndex(0, 'ArrowLeft', 3), 2);
	assert.equal(nextIndex(1, 'ArrowDown', 3), 2);
	assert.equal(nextIndex(1, 'ArrowUp', 3), 0);
});
test('nextIndex: Home/End', () => {
	assert.equal(nextIndex(1, 'Home', 4), 0);
	assert.equal(nextIndex(1, 'End', 4), 3);
});
test('nextIndex: 비활성 항목을 건너뛴다', () => {
	assert.equal(nextIndex(0, 'ArrowRight', 3, [false, true, false]), 2);
	assert.equal(nextIndex(2, 'ArrowLeft', 3, [false, true, false]), 0);
	assert.equal(nextIndex(1, 'Home', 3, [true, false, false]), 1);
	assert.equal(nextIndex(1, 'End', 3, [false, false, true]), 1);
});
test('nextIndex: 다른 키·빈 목록·전부 비활성', () => {
	assert.equal(nextIndex(1, 'a', 3), 1);
	assert.equal(nextIndex(0, 'ArrowRight', 0), -1);
	assert.equal(nextIndex(1, 'ArrowRight', 2, [true, true]), 1);
});
