// lib/loadFailure.ts — 실패 분류·문구·nullOn404 (ERR-1·6·8·9). 실행: npm run test:unit
import test from 'node:test';
import assert from 'node:assert/strict';
import { ApiError } from '../src/lib/api/client.ts';
import { classifyFailure, failureMessage, nullOn404, toResult } from '../src/lib/loadFailure.ts';

const err = (status, code) => new ApiError(status, { error: { code, message: 'm' } });

test('분류 — 404/네트워크/서버/abort', () => {
	assert.equal(classifyFailure(err(404, 'NOT_FOUND')).kind, 'not_found');
	assert.equal(classifyFailure(err(0, 'NETWORK')).kind, 'network');
	assert.equal(classifyFailure(err(0, 'ABORTED')).kind, 'aborted');
	assert.equal(classifyFailure(err(500, 'X')).kind, 'server');
	assert.equal(classifyFailure(err(502, 'BAD_RESPONSE')).kind, 'server');
});

test('404 를 뺀 4xx 는 server (ERR-8)', () => {
	assert.equal(classifyFailure(err(400, 'BAD')).kind, 'server');
	assert.equal(classifyFailure(err(409, 'CONFLICT')).kind, 'server');
});

test('임의 예외는 server + console.error 1회 + detail=오류 이름 (ERR-9)', () => {
	const orig = console.error;
	let n = 0;
	console.error = () => n++;
	try {
		const f = classifyFailure(new TypeError('x'));
		assert.equal(f.kind, 'server');
		assert.equal(f.detail, 'TypeError');
		assert.equal(f.code, 'UNKNOWN');
		assert.equal(n, 1);
		classifyFailure(err(500, 'X'));
		assert.equal(n, 1);
	} finally {
		console.error = orig;
	}
});

test('문구는 연결 끊김/서버 오류 두 가지 (ERR-1)', () => {
	assert.match(failureMessage('network'), /연결/);
	assert.match(failureMessage('server'), /서버 오류/);
	assert.equal(failureMessage('aborted'), failureMessage('server'));
});

test('nullOn404 — 404 만 null, 나머지는 다시 던진다', async () => {
	assert.equal(await nullOn404(Promise.reject(err(404, 'NOT_FOUND'))), null);
	assert.equal(await nullOn404(Promise.resolve(5)), 5);
	await assert.rejects(nullOn404(Promise.reject(err(500, 'X'))));
});

test('toResult — 성공/실패 래핑', async () => {
	assert.deepEqual(await toResult(Promise.resolve(1)), { ok: true, data: 1 });
	const r = await toResult(Promise.reject(err(0, 'NETWORK')));
	assert.equal(r.ok, false);
	assert.equal(r.failure.kind, 'network');
});
