import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { coverageLevels, trailingGap, coverageNote } from '../src/lib/coverage.ts';

describe('coverageLevels', () => {
	it('[0,2,10,5,1] → [0,1,3,2,1]', () => {
		assert.deepStrictEqual(coverageLevels([0, 2, 10, 5, 1]), [0, 1, 3, 2, 1]);
	});

	it('[0,0] → [0,0]', () => {
		assert.deepStrictEqual(coverageLevels([0, 0]), [0, 0]);
	});
});

describe('trailingGap', () => {
	it('[3,0,0,0,0] → 3', () => {
		assert.strictEqual(trailingGap([3, 0, 0, 0, 0]), 3);
	});

	it('[3,2,0,0] → 1', () => {
		assert.strictEqual(trailingGap([3, 2, 0, 0]), 1);
	});

	it('[0,0,0] → null', () => {
		assert.strictEqual(trailingGap([0, 0, 0]), null);
	});

	it('[1,1,1] → 0', () => {
		assert.strictEqual(trailingGap([1, 1, 1]), 0);
	});
});

describe('coverageNote', () => {
	it('[3,0,0,0,0] starts with 최근 3개월', () => {
		const note = coverageNote([3, 0, 0, 0, 0]);
		assert.ok(note?.startsWith('최근 3개월'), `got: ${note}`);
	});

	it('[3,2,0,0] → null (gap=1)', () => {
		assert.strictEqual(coverageNote([3, 2, 0, 0]), null);
	});
});
