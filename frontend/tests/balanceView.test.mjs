// lib/balanceView.ts — 상태·기준 텍스트, 요약 문장, 표 행(모든 축·기준·상태 포함), 주석, date 파라미터 (§8 T4·T6).
import test from 'node:test';
import assert from 'node:assert/strict';
import { summarySentence, tableRows, noteTexts, parseDateParam, formatValue, statusText, COLLECTING } from '../src/lib/balanceView.ts';
import { ApiError } from '../src/lib/api/client.ts';
import { toResult } from '../src/lib/loadFailure.ts';

const ax = (key, label, score, status, extra = {}) => ({
	key, label, unit: '%', actual: 10, target: 20, basis: 'default_rule', score, band: [80, 120], status,
	reason: score == null ? 'insufficient_runs' : null, reason_text: score == null ? '기록이 적어요' : null,
	source: [], computed_on: '2026-11-06', stale: false, ...extra
});
const data = (axes, extra = {}) => ({
	as_of: '2026-11-06', window_weeks: 8, state: 'ready', axes,
	compare: { as_of: '2026-10-09', axes: [{ key: 'quality', score: 58 }] },
	aux: { tsb: 7, monotony: 0.98, tanda_required_km: 96.6, tids_pattern: 'pyramidal', race_share_of_quality: null },
	notes: ['quality_includes_races'], stale_text: '입력이 오래됐어요', ...extra
});

test('요약 — 벗어난 축 나열 + 나머지 균형, 결측 수', () => {
	assert.equal(summarySentence([ax('quality', '품질 강도', 70, 'low'), ax('easy_base', '이지 기반', 100, 'balanced')]), '품질 강도 부족, 나머지 균형');
	assert.equal(summarySentence([ax('load', '부하 균형', 100, 'balanced'), ax('recovery', '회복', null, null)]), '모든 축 균형 (1개 축 데이터 수집 중)');
	assert.equal(summarySentence([ax('recovery', '회복', null, null)]), COLLECTING);
});

test('표 행 — 모든 축·기준·상태 텍스트, 결측 사유, 28일 전', () => {
	const rows = tableRows(data([ax('quality', '품질 강도', 84.5, 'balanced'), ax('load', '부하 균형', null, null, { unit: 'ACWR' })]));
	assert.equal(rows.length, 2);
	assert.equal(rows[0].basis, '기본 기준');
	assert.equal(rows[0].status, '균형');
	assert.equal(rows[0].score, '85');
	assert.equal(rows[0].compare, '58');
	assert.equal(rows[1].status, COLLECTING);
	assert.equal(rows[1].reason, '기록이 적어요');
	assert.equal(rows[1].compare, '—');
	assert.equal(statusText('high'), '과다');
});

test('값 표시 — 회복은 %, 부하는 소수 둘째, km 단위', () => {
	assert.equal(formatValue(1.014, { key: 'recovery', unit: '기준선 대비' }), '101%');
	assert.equal(formatValue(1.1, { key: 'load', unit: 'ACWR' }), '1.10');
	assert.equal(formatValue(35.5, { key: 'volume', unit: 'km/주' }), '35.5 km/주');
	assert.equal(formatValue(null, { key: 'volume', unit: 'km/주' }), '—');
});

test('주석 — 서버 notes + 기본 기준 가정 안내', () => {
	const t = noteTexts(data([ax('quality', '품질 강도', 84.5, 'balanced')]));
	assert.equal(t.length, 2);
	assert.ok(t[1].includes('가정'));
});

test('date 파라미터 — 형식 외는 null', () => {
	assert.equal(parseDateParam('2026-11-06'), '2026-11-06');
	assert.equal(parseDateParam('2026-1-6'), null);
	assert.equal(parseDateParam(null), null);
});

test('로더 실패 — toResult 가 LoadFailure 용 failure 로 분류', async () => {
	const r = await toResult(Promise.reject(new ApiError(503, { error: { code: 'NOT_FOUND', message: 'x' } })));
	assert.equal(r.ok, false);
	assert.equal(r.failure.kind, 'server');
});
