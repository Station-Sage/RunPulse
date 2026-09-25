import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { staleLabel } from '../src/lib/threadAge.ts';

const nowMs = Date.parse('2026-09-25T00:00:00Z');

describe('staleLabel', () => {
	it('14일 전 → 당시 기준 레이블', () => {
		assert.equal(staleLabel('2026-09-10 10:00:00', nowMs), '14일 전 대화 · 당시 기준');
	});

	it('1일 전 → null', () => {
		assert.equal(staleLabel('2026-09-24 10:00:00', nowMs), null);
	});

	it('null → null', () => {
		assert.equal(staleLabel(null, nowMs), null);
	});

	it('잘못된 문자열 → null', () => {
		assert.equal(staleLabel('not-a-date', nowMs), null);
	});
});
