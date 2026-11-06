import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { ApiError } from '../src/lib/api/client.ts';
import {
	attemptsLeft,
	formatRemaining,
	garminErrorText,
	isValidCode,
	last30Range,
	stepAfter
} from '../src/lib/garminConnect.ts';

const err = (status, code, message = '', details) => new ApiError(status, { error: { code, message, details } });

test('stepAfter: needs_mfa → mfa, connected → done', () => {
	assert.equal(stepAfter({ status: 'needs_mfa' }), 'mfa');
	assert.equal(stepAfter({ status: 'connected' }), 'done');
	assert.equal(stepAfter({ status: 'x' }), 'credentials');
});

test('isValidCode: 6~8자리 숫자만', () => {
	assert.ok(isValidCode('123456') && isValidCode(' 12345678 '));
	assert.ok(!isValidCode('12345') && !isValidCode('123456789') && !isValidCode('12a456'));
});

test('MFA 오답: 남은 시도 표시 + 코드 지움, 단계 유지', () => {
	const e = err(422, 'MFA_INVALID', '', { attempts_left: 3 });
	assert.equal(attemptsLeft(e), 3);
	const v = garminErrorText(e, 'mfa');
	assert.match(v.text, /남은 시도 3번/);
	assert.equal(v.clearCode, true);
	assert.equal(v.resetTo, undefined);
});

test('MFA 만료·MFA 불가 → 처음 단계로', () => {
	assert.equal(garminErrorText(err(410, 'MFA_EXPIRED'), 'mfa').resetTo, 'credentials');
	assert.equal(garminErrorText(err(503, 'MFA_UNAVAILABLE'), 'login').resetTo, 'credentials');
});

test('인증 실패 문구는 모드별, 세션 만료(AUTH_REQUIRED)와 구분', () => {
	assert.equal(garminErrorText(err(401, 'GARMIN_AUTH_FAILED'), 'login').text, '이메일 또는 비밀번호가 맞지 않아요');
	assert.match(garminErrorText(err(401, 'GARMIN_AUTH_FAILED'), 'token').text, /토큰/);
	assert.match(garminErrorText(err(401, 'AUTH_REQUIRED'), 'login').text, /로그인이 만료/);
});

test('레이트리밋·상류 오류·검증 오류 문구', () => {
	assert.match(garminErrorText(err(503, 'GARMIN_RATE_LIMITED'), 'login').text, /15분/);
	assert.match(garminErrorText(err(429, 'RATE_LIMITED'), 'login').text, /너무 많아요/);
	assert.match(garminErrorText(err(502, 'GARMIN_UPSTREAM'), 'login').text, /연결하지 못했어요/);
	assert.equal(garminErrorText(err(400, 'INVALID_PARAM', '이메일을 확인해 주세요'), 'login').text, '이메일을 확인해 주세요');
	assert.match(garminErrorText(err(0, 'NETWORK'), 'login').text, /연결이 끊겨/);
});

test('formatRemaining·last30Range', () => {
	assert.equal(formatRemaining(300), '5:00');
	assert.equal(formatRemaining(65.9), '1:05');
	assert.equal(formatRemaining(-3), '0:00');
	assert.deepEqual(last30Range(new Date(2026, 2, 5)), { from: '2026-02-03', to: '2026-03-05' });
});

test('시트: ticket 은 메모리에만, 비밀번호 필드 자동완성 속성', () => {
	const src = readFileSync('src/lib/components/data/GarminConnectSheet.svelte', 'utf8');
	assert.ok(!/localStorage|sessionStorage|searchParams/.test(src));
	assert.match(src, /autocomplete="current-password"/);
	assert.match(src, /autocomplete="one-time-code"/);
	assert.match(src, /inputmode="numeric"/);
});

test('v2 화면에 v1 Garmin 연결 링크가 남지 않는다', () => {
	for (const f of ['src/lib/components/data/ConnectPanel.svelte', 'src/lib/components/welcome/Step1Connect.svelte']) {
		assert.ok(!readFileSync(f, 'utf8').includes('/connect/garmin'), f);
	}
});
