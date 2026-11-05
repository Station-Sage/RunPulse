// lib/auth/guard.ts · loadFailure auth 분류 · apiFetch opaqueredirect. 실행: npm run test:unit
import test from 'node:test';
import assert from 'node:assert/strict';
import { authRedirect, loginHref, inviteErrorMessage, isPublicRoute } from '../src/lib/auth/guard.ts';
import { ApiError } from '../src/lib/api/client.ts';
import { classifyFailure, failureMessage } from '../src/lib/loadFailure.ts';

const S = (state, mode = 'registry') => ({ mode, state, email: null });

test('공개 경로 판정', () => {
	for (const p of ['/landing', '/demo', '/auth/login', '/auth/pending']) assert.ok(isPublicRoute(p), p);
	assert.ok(!isPublicRoute('/today'));
	assert.ok(!isPublicRoute('/landingx'));
});

test('익명은 보호 경로에서 landing 으로, 공개 경로는 통과', () => {
	assert.equal(authRedirect(S('anonymous'), '/today', false), '/landing');
	assert.equal(authRedirect(S('anonymous'), '/landing', false), null);
	assert.equal(authRedirect(S('anonymous'), '/auth/login', false), null);
});

test('pending 은 /auth/pending 으로', () => {
	assert.equal(authRedirect(S('pending'), '/today', false), '/auth/pending');
	assert.equal(authRedirect(S('pending'), '/auth/pending', false), null);
	assert.equal(authRedirect(S('pending'), '/landing', false), null);
});

test('active 는 landing·auth 화면에서 /today 로', () => {
	assert.equal(authRedirect(S('active'), '/landing', false), '/today');
	assert.equal(authRedirect(S('active'), '/auth/login', false), '/today');
	assert.equal(authRedirect(S('active'), '/coach', false), null);
});

test('legacy 모드·데모·세션 조회 실패는 가드하지 않는다', () => {
	assert.equal(authRedirect(S('anonymous', 'legacy'), '/today', false), null);
	assert.equal(authRedirect(S('anonymous'), '/today', true), null);
	assert.equal(authRedirect(null, '/today', false), null);
});

test('loginHref — 안전하지 않은 next 는 /v2/today', () => {
	assert.equal(loginHref('/v2/coach'), '/auth/start?next=%2Fv2%2Fcoach');
	for (const bad of ['https://evil.com', '//evil.com', '/v2//x', '/other', '/v2/a?b=1'])
		assert.equal(loginHref(bad), '/auth/start?next=%2Fv2%2Ftoday', bad);
});

test('초대 오류 문구', () => {
	assert.match(inviteErrorMessage(400, 'INVITE_INVALID'), /초대코드/);
	assert.match(inviteErrorMessage(429, 'RATE_LIMITED'), /너무 많/);
	assert.match(inviteErrorMessage(429, 'SIGNUP_CAP'), /가득/);
	assert.match(inviteErrorMessage(403, 'NOT_ALLOWED'), /허용/);
	assert.match(inviteErrorMessage(503, 'PROVISION_FAILED'), /준비/);
});

test('AUTH_REQUIRED → auth 분류 + 문구', () => {
	const f = classifyFailure(new ApiError(401, { error: { code: 'AUTH_REQUIRED', message: 'x' } }));
	assert.equal(f.kind, 'auth');
	assert.match(failureMessage('auth'), /로그인/);
});

test('apiFetch — opaqueredirect 는 AUTH_REQUIRED', async () => {
	const { apiFetch } = await import('../src/lib/api/client.ts');
	const orig = globalThis.fetch;
	globalThis.fetch = async () => ({ type: 'opaqueredirect', status: 0, ok: false });
	try {
		await assert.rejects(apiFetch('/today'), (e) => e.code === 'AUTH_REQUIRED' && e.status === 401);
	} finally {
		globalThis.fetch = orig;
	}
});
