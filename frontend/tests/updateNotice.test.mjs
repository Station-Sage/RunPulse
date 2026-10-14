import test from 'node:test';
import assert from 'node:assert/strict';
import { get } from 'svelte/store';
import {
	CHECK_MIN_INTERVAL_MS, NOTICE_STORAGE_KEY, notifyUpdate, shouldCheck, shouldNotify, updateNoticeVisible
} from '../src/lib/updateNotice.ts';

function memStorage(init = {}) {
	const m = new Map(Object.entries(init));
	return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => void m.set(k, String(v)), _m: m };
}

test('shouldNotify: first time per build is true, repeat on same build is false', () => {
	const s = memStorage();
	assert.equal(shouldNotify(s, 'b1'), true);
	assert.equal(s._m.get(NOTICE_STORAGE_KEY), 'b1');
	assert.equal(shouldNotify(s, 'b1'), false);
	assert.equal(shouldNotify(s, 'b1'), false);
});

test('shouldNotify: a different build notifies again', () => {
	const s = memStorage({ [NOTICE_STORAGE_KEY]: 'b1' });
	assert.equal(shouldNotify(s, 'b2'), true);
	assert.equal(shouldNotify(s, 'b2'), false);
});

test('shouldNotify: no storage or throwing storage still notifies (alert wins)', () => {
	assert.equal(shouldNotify(null, 'b1'), true);
	assert.equal(shouldNotify(undefined, 'b1'), true);
	const boom = { getItem() { throw new Error('denied'); }, setItem() { throw new Error('denied'); } };
	assert.equal(shouldNotify(boom, 'b1'), true);
	const failWrite = { getItem: () => null, setItem() { throw new Error('quota'); } };
	assert.equal(shouldNotify(failWrite, 'b1'), true);
});

test('shouldCheck: first check, then respects min interval', () => {
	assert.equal(shouldCheck(null, 1000), true);
	assert.equal(shouldCheck(1000, 1000 + CHECK_MIN_INTERVAL_MS - 1), false);
	assert.equal(shouldCheck(1000, 1000 + CHECK_MIN_INTERVAL_MS), true);
	assert.equal(shouldCheck(1000, 1500, 100), true);
});

test('notifyUpdate sets the visible store once per build and never auto-reloads', () => {
	updateNoticeVisible.set(false);
	globalThis.location = { reload() { throw new Error('must not auto reload'); } };
	const s = memStorage();
	assert.equal(notifyUpdate(s, 'b9'), true);
	assert.equal(get(updateNoticeVisible), true);
	updateNoticeVisible.set(false);               // 사용자가 '나중에'
	assert.equal(notifyUpdate(s, 'b9'), false);   // 같은 빌드 — 다시 띄우지 않음
	assert.equal(get(updateNoticeVisible), false);
	assert.equal(notifyUpdate(s, 'b10'), true);   // 더 새로운 빌드 — 다시 알림
	assert.equal(get(updateNoticeVisible), true);
	delete globalThis.location;
});
