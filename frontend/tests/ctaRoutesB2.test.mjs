import test from 'node:test';
import assert from 'node:assert/strict';
import { SOURCE_CONNECT, PLAN_HOME, sessionDetail, planDetail } from '../src/lib/ctaRoutes.ts';

test('소스 연결 목적지는 /data/sources', () => assert.equal(SOURCE_CONNECT, '/data/sources'));
test('세션 상세: 목표·날짜 있으면 세션 페이지', () =>
	assert.equal(sessionDetail(3, '2026-11-20'), '/coach/plan/3/session/2026-11-20'));
test('세션 상세: 정보 없으면 플랜 홈', () => {
	assert.equal(sessionDetail(null, '2026-11-20'), PLAN_HOME);
	assert.equal(sessionDetail(3, undefined), PLAN_HOME);
});
test('planDetail', () => assert.equal(planDetail(7), '/coach/plan/7'));
