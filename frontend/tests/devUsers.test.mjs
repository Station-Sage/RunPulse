import test from 'node:test';
import assert from 'node:assert/strict';
import { UID_HINT, isSameUser, pickUserId, uidProblem } from '../src/lib/devUsers.ts';

// 서버 `validate_uid`(tests/test_user_context.py) 와 같은 판정이어야 한다 — 입력 즉시 안내용 사본.
test('uidProblem accepts email-style and default ids', () => {
	for (const ok of ['default', 'user@example.com', 'a.b_c-d+e%f@x.co', 'a'.repeat(254), '  pad@example.com  ']) {
		assert.equal(uidProblem(ok), null, ok);
	}
});

test('uidProblem rejects path-like, hidden and out-of-charset ids', () => {
	for (const bad of ['.', '..', '../x', 'a/b', 'a\\b', '.hidden', 'a b', 'é', 'a'.repeat(255), 'a\nb']) {
		assert.equal(uidProblem(bad), UID_HINT, JSON.stringify(bad));
	}
});

test('uidProblem asks for input when empty or blank', () => {
	assert.equal(uidProblem(''), '사용자 이름을 입력하세요');
	assert.equal(uidProblem('   '), '사용자 이름을 입력하세요');
});

test('pickUserId prefers typed over selected and trims', () => {
	assert.equal(pickUserId('a@x.com', ''), 'a@x.com');
	assert.equal(pickUserId('a@x.com', '  b@x.com '), 'b@x.com');
	assert.equal(pickUserId('', ''), '');
});

test('isSameUser compares trimmed target with current', () => {
	assert.equal(isSameUser(' a@x.com ', 'a@x.com'), true);
	assert.equal(isSameUser('b@x.com', 'a@x.com'), false);
});
