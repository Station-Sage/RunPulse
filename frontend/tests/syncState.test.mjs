import { test } from 'node:test';
import assert from 'node:assert/strict';
import { pillView, sourceLine, relativeAgo } from '../src/lib/syncState.ts';

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
