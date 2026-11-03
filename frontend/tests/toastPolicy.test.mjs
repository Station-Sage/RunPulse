import test from 'node:test';
import assert from 'node:assert/strict';
import { toastPolicy } from '../src/lib/a11y/toastPolicy.ts';

test('info 토스트는 polite + 자동 닫힘', () => {
	assert.deepEqual(toastPolicy('info'), { politeness: 'polite', autoCloseMs: 5000 });
	assert.equal(toastPolicy('info', 3000).autoCloseMs, 3000);
});

test('error 토스트는 assertive + 자동 닫힘 없음', () => {
	assert.deepEqual(toastPolicy('error'), { politeness: 'assertive', autoCloseMs: null });
});
