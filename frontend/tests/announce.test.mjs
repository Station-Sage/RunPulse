import test from 'node:test';
import assert from 'node:assert/strict';
import { createAnnouncer } from '../src/lib/a11y/announce.ts';

function setup() {
	let t = 0;
	const a = createAnnouncer(() => t);
	const got = [];
	a.subscribe((l, x) => got.push([l, x]));
	return { a, got, tick: (ms) => (t += ms) };
}

test('빈 문자열·null 은 무시', () => {
	const { a, got } = setup();
	assert.equal(a.announce(''), false);
	assert.equal(a.announce('  '), false);
	assert.equal(a.announce(null), false);
	assert.deepEqual(got, []);
});

test('기본은 polite, assertive 지정 가능', () => {
	const { a, got } = setup();
	a.announce('저장했어요');
	a.announce('실패했어요', 'assertive');
	assert.deepEqual(got, [['polite', '저장했어요'], ['assertive', '실패했어요']]);
});

test('1초 안 같은 문구는 무시, 이후엔 다시 발신', () => {
	const { a, got, tick } = setup();
	a.announce('완료');
	tick(500);
	assert.equal(a.announce('완료'), false);
	tick(600);
	assert.equal(a.announce('완료'), true);
	assert.equal(got.length, 2);
});

test('같은 문구라도 level 이 다르면 별개', () => {
	const { a, got } = setup();
	a.announce('x');
	a.announce('x', 'assertive');
	assert.equal(got.length, 2);
});

test('구독 해제', () => {
	const a = createAnnouncer(() => 0);
	const got = [];
	const off = a.subscribe((l, x) => got.push(x));
	off();
	a.announce('y');
	assert.deepEqual(got, []);
});
