import test from 'node:test';
import assert from 'node:assert/strict';
import { isDismissed, dismiss } from '../src/lib/checkinDismiss.ts';

const mem = () => {
	const m = new Map();
	return { getItem: (k) => m.get(k) ?? null, setItem: (k, v) => void m.set(k, v) };
};

test('dismiss는 날짜별로 기억된다', () => {
	const s = mem();
	assert.equal(isDismissed('2026-09-29', s), false);
	dismiss('2026-09-29', s);
	assert.equal(isDismissed('2026-09-29', s), true);
	assert.equal(isDismissed('2026-09-30', s), false);
});

test('저장소가 없거나 던져도 안전하다', () => {
	assert.equal(isDismissed('2026-09-29', null), false);
	dismiss('2026-09-29', null);
	const bad = { getItem: () => { throw new Error('x'); }, setItem: () => { throw new Error('x'); } };
	assert.equal(isDismissed('2026-09-29', bad), false);
	dismiss('2026-09-29', bad);
});

test('빈 날짜는 무시한다', () => {
	const s = mem();
	dismiss('', s);
	assert.equal(isDismissed('', s), false);
});
