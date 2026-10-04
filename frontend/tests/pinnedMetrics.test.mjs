import { test } from 'node:test';
import assert from 'node:assert/strict';
import { loadPins, savePins, togglePin, DEFAULT_PINS } from '../src/lib/pinnedMetrics.ts';

const mem = (init) => {
	let v = init ?? null;
	return { getItem: () => v, setItem: (_k, x) => { v = x; } };
};

test('저장값 없으면 기본 세트', () => assert.deepEqual(loadPins(mem()), DEFAULT_PINS));
test('손상된 값은 기본 세트', () => {
	assert.deepEqual(loadPins(mem('{bad')), DEFAULT_PINS);
	assert.deepEqual(loadPins(mem('[1,2]')), DEFAULT_PINS);
});
test('저장 후 복원', () => {
	const s = mem();
	savePins(['ctl'], s);
	assert.deepEqual(loadPins(s), ['ctl']);
});
test('토글 추가/제거', () => {
	assert.deepEqual(togglePin(['a'], 'b'), ['a', 'b']);
	assert.deepEqual(togglePin(['a', 'b'], 'a'), ['b']);
});
