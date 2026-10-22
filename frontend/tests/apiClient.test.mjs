// lib/api/client.ts apiFetch 정규화 — fetch 스텁 (design error-retry-common §2.1).
import test from 'node:test';
import assert from 'node:assert/strict';
import { apiFetch, ApiError } from '../src/lib/api/client.ts';

async function failWith(fetchImpl) {
	const orig = globalThis.fetch;
	globalThis.fetch = fetchImpl;
	try {
		await apiFetch('/x');
		assert.fail('should throw');
	} catch (e) {
		return e;
	} finally {
		globalThis.fetch = orig;
	}
}

test('fetch TypeError → NETWORK(0)', async () => {
	const e = await failWith(async () => {
		throw new TypeError('Failed to fetch');
	});
	assert.ok(e instanceof ApiError);
	assert.equal(e.status, 0);
	assert.equal(e.code, 'NETWORK');
});

test('AbortError → ABORTED(0)', async () => {
	const e = await failWith(async () => {
		throw new DOMException('aborted', 'AbortError');
	});
	assert.equal(e.code, 'ABORTED');
});

test('비JSON 응답 → BAD_RESPONSE(status 유지)', async () => {
	const e = await failWith(async () => new Response('<html>502</html>', { status: 502 }));
	assert.ok(e instanceof ApiError);
	assert.equal(e.status, 502);
	assert.equal(e.code, 'BAD_RESPONSE');
});

test('JSON 오류 본문은 기존대로 ApiError', async () => {
	const e = await failWith(
		async () => new Response(JSON.stringify({ error: { code: 'NOT_FOUND', message: 'n' } }), { status: 404 })
	);
	assert.equal(e.status, 404);
	assert.equal(e.code, 'NOT_FOUND');
});

test('성공 시 data 반환', async () => {
	const orig = globalThis.fetch;
	globalThis.fetch = async () => new Response(JSON.stringify({ data: { a: 1 } }), { status: 200 });
	try {
		assert.deepEqual(await apiFetch('/x'), { a: 1 });
	} finally {
		globalThis.fetch = orig;
	}
});
