import { test } from 'node:test';
import assert from 'node:assert/strict';
import { pillView, sourceLine, relativeAgo, pollIntervalMs } from '../src/lib/syncState.ts';

const NOW = new Date('2026-09-27T21:00:00+09:00');
const src = (over) => ({
	provider: 'garmin', connection: 'connected', enabled: true, state: 'idle-ok',
	last_attempt_at: null, last_success_at: '2026-09-27T20:57:00+09:00', last_new_data_at: null,
	last_error: null, running: null, ...over
});
const state = (over) => ({
	as_of: NOW.toISOString(), latest_data_date: '2026-09-27',
	overall: { level: 'ok', label_ko: '', last_success_at: '2026-09-27T20:57:00+09:00' },
	connected_count: 1, first_sync_running: false, sources: [src({})], caveats: [], open_errors: 0, ...over
});

test('relativeAgo: 분/시간/일 단위', () => {
	assert.equal(relativeAgo('2026-09-27T20:59:30+09:00', NOW), '방금');
	assert.equal(relativeAgo('2026-09-27T20:57:00+09:00', NOW), '3분 전');
	assert.equal(relativeAgo('2026-09-27T16:00:00+09:00', NOW), '5시간 전');
	assert.equal(relativeAgo('2026-09-25T20:00:00+09:00', NOW), '2일 전');
	assert.equal(relativeAgo(null, NOW), null);
});

test('pillView: 상태 null/미연결/정상/지연/오류/진행', () => {
	assert.equal(pillView(null, NOW).tone, 'empty');
	assert.equal(pillView(state({ connected_count: 0 }), NOW).text, '기기 연결');
	assert.deepEqual(pillView(state({}), NOW), { tone: 'ok', glyph: '●', text: '9/27 · 3분 전' });
	const stale = pillView(state({ overall: { level: 'stale', label_ko: '', last_success_at: '2026-09-26T20:00:00+09:00' }, latest_data_date: '2026-09-26' }), NOW);
	assert.equal(stale.tone, 'stale');
	assert.equal(stale.text, '9/26 기준 · 25시간 전'.replace('25시간', '1일'));
	const err = pillView(state({ overall: { level: 'error', label_ko: '', last_success_at: null }, sources: [src({ provider: 'strava', state: 'error-access' })] }), NOW);
	assert.deepEqual(err, { tone: 'error', glyph: '▲', text: 'Strava 확인 필요' });
	const run = pillView(state({ overall: { level: 'running', label_ko: '', last_success_at: null }, sources: [src({ state: 'running' })] }), NOW);
	assert.equal(run.text, '동기화 중 1');
});

test('sourceLine: 소스 행 문구', () => {
	assert.equal(sourceLine(src({}), NOW).text, '3분 전');
	assert.equal(sourceLine(src({ state: 'not_connected' }), NOW).text, '미연결');
	assert.equal(sourceLine(src({ state: 'disabled' }), NOW).glyph, '○');
	assert.equal(sourceLine(src({ state: 'running', running: { job_id: 1, progress_pct: 40 } }), NOW).text, '동기화 중 40%');
	assert.equal(sourceLine(src({ state: 'error-access', last_error: { code: 'subscription_required', message_ko: '접근 차단(403)', action: 'x' } }), NOW).text, '접근 차단(403)');
});

test('pollIntervalMs: 진행 중 5초, 평시·null 60초', () => {
	assert.equal(pollIntervalMs(null), 60000);
	assert.equal(pollIntervalMs(state({})), 60000);
	assert.equal(pollIntervalMs(state({ first_sync_running: true })), 5000);
	assert.equal(pollIntervalMs(state({ sources: [src({ state: 'running' })] })), 5000);
});

import {
	triggerButtonView, outcomeFromError, outcomeFromResponse, waitLabel, skipLine
} from '../src/lib/syncState.ts';

const ctx = (over) => ({ triggering: false, cooldownUntil: null, now: 1_000_000, ...over });

test('triggerButtonView: 연결·활성 소스 0개면 설정 링크 + 비활성', () => {
	const v = triggerButtonView(state({ sources: [src({ connection: 'not_connected', state: 'not_connected' })] }), ctx());
	assert.equal(v.disabled, true);
	assert.equal(v.settingsLink, true);
});

test('triggerButtonView: 요청 중 / 진행 중 / 쿨다운 / 기본', () => {
	const s = state({ sources: [src(), src({ provider: 'strava' })] });
	assert.deepEqual(triggerButtonView(s, ctx({ triggering: true })), { label: '요청 중…', disabled: true });
	const run = state({ sources: [src({ state: 'running' }), src({ provider: 'strava' })] });
	assert.equal(triggerButtonView(run, ctx()).label, '동기화 중 1/2');
	assert.equal(triggerButtonView(s, ctx({ cooldownUntil: 1_000_000 + 120_000 })).label, '2분 후 가능');
	assert.deepEqual(triggerButtonView(s, ctx({ cooldownUntil: 999_000 })), { label: '지금 동기화', disabled: false });
});

test('pollIntervalMs: 트리거 후 15초는 5초 주기', () => {
	const idle = state({ sources: [src()] });
	assert.equal(pollIntervalMs(idle, 1000, 5000), 5000);
	assert.equal(pollIntervalMs(idle, 1000, 16001), 60000);
	assert.equal(pollIntervalMs(idle, null, 5000), 60000);
});

test('outcomeFromError: 상태코드별 문구', () => {
	assert.equal(outcomeFromError(409, null).kick, true);
	const c = outcomeFromError(429, { retry_after_sec: 90, skipped: [{ provider: 'garmin', code: 'cooldown', message_ko: 'x', retry_after_sec: 90 }] });
	assert.equal(c.cooldownSec, 90);
	assert.equal(c.skipped.length, 1);
	assert.match(outcomeFromError(422, null).notice, /연결된 소스/);
	assert.match(outcomeFromError(0, null).notice, /다시 눌러/);
	assert.equal(outcomeFromError(500, null).kick, false);
});

test('outcomeFromResponse / waitLabel / skipLine', () => {
	const o = outcomeFromResponse({ runs: [], skipped: [{ provider: 'strava', code: 'cooldown', message_ko: 'm', retry_after_sec: 61 }] });
	assert.equal(o.kick, true);
	assert.equal(waitLabel(30), '30초 후 가능');
	assert.equal(skipLine(o.skipped[0]), '⏱ Strava 2분 후 가능');
	assert.equal(skipLine({ provider: 'garmin', code: 'running', message_ko: '' }), 'Garmin 이미 동기화 중');
});

test('outcomeFromResponse: 미연결·꺼짐 skip은 안내 줄에서 제외', () => {
	const o = outcomeFromResponse({ runs: [], skipped: [
		{ provider: 'garmin', code: 'not_connected', message_ko: 'a' },
		{ provider: 'strava', code: 'disabled', message_ko: 'b' },
		{ provider: 'intervals', code: 'cooldown', message_ko: 'c', retry_after_sec: 60 }] });
	assert.deepEqual(o.skipped.map((x) => x.provider), ['intervals']);
});

import { justFinished, completionSummary } from '../src/lib/syncState.ts';

const mk = (...pairs) => ({
	sources: pairs.map(([provider, state]) => ({ provider, state }))
});

test('justFinished: running → 비실행일 때만 true', () => {
	assert.equal(justFinished(mk(['garmin', 'running']), mk(['garmin', 'idle-ok'])), true);
	assert.equal(justFinished(mk(['garmin', 'idle-ok']), mk(['garmin', 'idle-ok'])), false);
	assert.equal(justFinished(mk(['garmin', 'running']), mk(['garmin', 'running'])), false);
	assert.equal(justFinished(null, mk(['garmin', 'idle-ok'])), false);
});

test('completionSummary: 갱신·확인 필요 집계, 전이 아니면 null', () => {
	const prev = mk(['garmin', 'running'], ['strava', 'running'], ['intervals', 'idle-ok']);
	const next = mk(['garmin', 'error-auth'], ['strava', 'idle-ok'], ['intervals', 'idle-ok']);
	assert.equal(completionSummary(prev, next), '동기화 완료 · 1개 소스 갱신 · Garmin 확인 필요');
	assert.equal(completionSummary(next, next), null);
	assert.equal(
		completionSummary(mk(['garmin', 'running']), mk(['garmin', 'idle-ok'])),
		'동기화 완료 · 1개 소스 갱신'
	);
});
