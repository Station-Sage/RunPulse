import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
	initialStream, applyEvent, isSlow, reconnectStep, stageLine, isPendingStatus, SLOW_MS
} from '../src/lib/coachStream.ts';

const run = (events) => events.reduce((s, [n, d, id]) => applyEvent(s, n, d, id), initialStream());

test('stage → delta → done: pending→working→streaming→done', () => {
	let s = initialStream();
	assert.equal(s.phase, 'pending');
	s = applyEvent(s, 'stage', { key: 'data', label: '데이터 확인 중' }, 1);
	assert.equal(s.phase, 'working');
	s = applyEvent(s, 'delta', { text: '안녕' }, 2);
	s = applyEvent(s, 'delta', { text: '하세요' }, 3);
	assert.equal(s.phase, 'streaming');
	assert.equal(s.text, '안녕하세요');
	s = applyEvent(s, 'done', { status: 'done' }, 4);
	assert.equal(s.phase, 'done');
	assert.ok(s.terminal);
});

test('같은 stage key는 갱신, 다른 key는 추가', () => {
	const s = run([
		['stage', { key: 'a', label: 'A1' }, 1],
		['stage', { key: 'a', label: 'A2' }, 2],
		['stage', { key: 'b', label: 'B' }, 3]
	]);
	assert.deepEqual(s.stages, [{ key: 'a', label: 'A2' }, { key: 'b', label: 'B' }]);
});

test('이미 본 id와 종료 후 이벤트는 무시', () => {
	let s = run([['delta', { text: 'x' }, 1], ['delta', { text: 'x' }, 1]]);
	assert.equal(s.text, 'x');
	s = applyEvent(s, 'done', { status: 'done' }, 2);
	s = applyEvent(s, 'delta', { text: 'late' }, 3);
	assert.equal(s.text, 'x');
});

test('fallback 오류 이벤트: 사유 기록, 이후 규칙 답변 delta가 이어지고 done(fallback)', () => {
	const s = run([
		['stage', { key: 'model', label: '작성' }, 1],
		['error', { status: 'fallback', reason: 'http_429', attempts: [] }, 2],
		['delta', { text: '규칙 답변' }, 3],
		['done', { status: 'fallback' }, 4]
	]);
	assert.equal(s.fallbackReason, 'http_429');
	assert.equal(s.text, '규칙 답변');
	assert.equal(s.phase, 'fallback');
});

test('error 이벤트(status=error)는 종료', () => {
	const s = run([['error', { status: 'error', reason: 'interrupted', attempts: [] }, 1]]);
	assert.equal(s.phase, 'error');
	assert.equal(s.errorReason, 'interrupted');
	assert.ok(s.terminal);
});

test('done(cancelled) → cancelled, 부분 텍스트 유지', () => {
	const s = run([['delta', { text: '부분' }, 1], ['done', { status: 'cancelled' }, 2]]);
	assert.equal(s.phase, 'cancelled');
	assert.equal(s.text, '부분');
});

test('isSlow: 20초 무응답이면 true, 종료 후엔 false', () => {
	const s = initialStream();
	assert.equal(isSlow(s, 0, SLOW_MS - 1), false);
	assert.equal(isSlow(s, 0, SLOW_MS), true);
	assert.equal(isSlow(applyEvent(s, 'done', { status: 'done' }, 1), 0, SLOW_MS * 2), false);
});

test('reconnectStep: 3회 실패 후 폴링', () => {
	assert.equal(reconnectStep(1), 'retry');
	assert.equal(reconnectStep(2), 'retry');
	assert.equal(reconnectStep(3), 'poll');
});

test('stageLine / isPendingStatus', () => {
	assert.equal(stageLine(initialStream()), '답변 준비 중…');
	const s = applyEvent(initialStream(), 'stage', { key: 'd', label: '데이터 확인 중: 최근 4주' }, 1);
	assert.equal(stageLine(s), '데이터 확인 중: 최근 4주…');
	assert.equal(isPendingStatus('pending'), true);
	assert.equal(isPendingStatus('working'), true);
	assert.equal(isPendingStatus('done'), false);
	assert.equal(isPendingStatus(undefined), false);
});
