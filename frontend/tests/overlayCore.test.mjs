// 오버레이 공통 코어(lib/overlayCore.ts) 순수 함수 테스트 — OVL 1단계.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
	createOverlayStack,
	nextFocusIndex,
	createScrollLock,
	FOCUSABLE_SELECTOR
} from '../src/lib/overlayCore.ts';

test('overlayStack — 비어 있으면 top null, isTop false', () => {
	const s = createOverlayStack();
	assert.equal(s.top(), null);
	assert.equal(s.isTop('a'), false);
});

test('overlayStack — 중첩: 맨 위만 isTop, pop 하면 아래가 top', () => {
	const s = createOverlayStack();
	s.push('drawer');
	s.push('sync');
	assert.equal(s.top(), 'sync');
	assert.equal(s.isTop('drawer'), false);
	s.pop('sync');
	assert.equal(s.isTop('drawer'), true);
});

test('overlayStack — 아래 항목을 먼저 pop 해도 위 항목이 top 유지', () => {
	const s = createOverlayStack();
	s.push('a');
	s.push('b');
	s.pop('a');
	assert.equal(s.top(), 'b');
	assert.equal(s.size(), 1);
});

test('overlayStack — 같은 id 재 push 는 중복 없이 맨 위로', () => {
	const s = createOverlayStack();
	s.push('a');
	s.push('b');
	s.push('a');
	assert.equal(s.size(), 2);
	assert.equal(s.top(), 'a');
});

test('overlayStack — 없는 id pop 은 무시', () => {
	const s = createOverlayStack();
	s.push('a');
	s.pop('zzz');
	assert.equal(s.top(), 'a');
});

test('nextFocusIndex — Tab 은 끝에서 처음으로 순환', () => {
	assert.equal(nextFocusIndex(3, 0, false), 1);
	assert.equal(nextFocusIndex(3, 2, false), 0);
});

test('nextFocusIndex — Shift+Tab 은 처음에서 끝으로 순환', () => {
	assert.equal(nextFocusIndex(3, 1, true), 0);
	assert.equal(nextFocusIndex(3, 0, true), 2);
});

test('nextFocusIndex — 포커스가 트랩 밖(-1)이면 방향별 처음/끝', () => {
	assert.equal(nextFocusIndex(4, -1, false), 0);
	assert.equal(nextFocusIndex(4, -1, true), 3);
});

test('nextFocusIndex — 요소 1개면 항상 0, 0개면 -1', () => {
	assert.equal(nextFocusIndex(1, 0, false), 0);
	assert.equal(nextFocusIndex(1, 0, true), 0);
	assert.equal(nextFocusIndex(0, 0, false), -1);
});

test('scrollLock — 0→1 에서만 lock, 1→0 에서만 unlock', () => {
	const calls = [];
	const l = createScrollLock(() => calls.push('lock'), () => calls.push('unlock'));
	l.acquire();
	l.acquire();
	assert.deepEqual(calls, ['lock']);
	l.release();
	assert.deepEqual(calls, ['lock']);
	l.release();
	assert.deepEqual(calls, ['lock', 'unlock']);
	assert.equal(l.count(), 0);
});

test('scrollLock — 과잉 release 는 음수가 되지 않고 unlock 을 반복하지 않는다', () => {
	const calls = [];
	const l = createScrollLock(() => calls.push('lock'), () => calls.push('unlock'));
	l.release();
	l.acquire();
	l.release();
	l.release();
	assert.deepEqual(calls, ['lock', 'unlock']);
	assert.equal(l.count(), 0);
});

test('FOCUSABLE_SELECTOR — disabled 와 tabindex=-1 제외 표기를 포함', () => {
	assert.match(FOCUSABLE_SELECTOR, /button:not\(\[disabled\]\)/);
	assert.match(FOCUSABLE_SELECTOR, /\[tabindex\]:not\(\[tabindex="-1"\]\)/);
});
